"""
Analytics engine using Pandas for GPA calculation, rankings, and at-risk detection.
"""
import pandas as pd
from database.connection import get_connection
from config import score_to_gpa4


def _load_grade_data(semester_id=None):
    """Load all grade data into a Pandas DataFrame, optionally filtered by semester."""
    query = """
        SELECT
            s.id AS student_id,
            s.student_code,
            s.name AS student_name,
            c.id AS course_id,
            c.course_code,
            c.name AS course_name,
            c.credits,
            c.semester_id,
            sem.name AS semester_name,
            e.id AS enrollment_id,
            a.type AS assignment_type,
            a.weight,
            a.max_score,
            g.score
        FROM Grades g
        JOIN Enrollments e ON g.enrollment_id = e.id
        JOIN Students s ON e.student_id = s.id
        JOIN Courses c ON e.course_id = c.id
        JOIN Semesters sem ON c.semester_id = sem.id
        JOIN Assignments a ON g.assignment_id = a.id
        WHERE e.status = 'active'
    """
    params = ()
    if semester_id:
        query += " AND c.semester_id = ?"
        params = (semester_id,)

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


def _calculate_course_grade(group):
    """Calculate weighted grade for a single enrollment group."""
    total = 0.0
    weight_sum = 0.0
    for _, row in group.iterrows():
        if pd.notna(row["score"]):
            total += (row["score"] / row["max_score"]) * row["weight"]
            weight_sum += row["weight"]
    if weight_sum == 0:
        return None
    return round((total / weight_sum) * 100, 2)


def get_student_course_grades(semester_id=None):
    """
    Returns a DataFrame with one row per student-course:
    student_id, student_name, course_code, course_name, credits, semester_name, final_grade, gpa_points
    """
    df = _load_grade_data(semester_id)
    if df.empty:
        return pd.DataFrame()

    results = []
    grouped = df.groupby(["student_id", "student_code", "student_name", "course_id",
                           "course_code", "course_name", "credits", "semester_id", "semester_name"])

    for keys, group in grouped:
        student_id, student_code, student_name, course_id, course_code, course_name, credits, sem_id, sem_name = keys
        final_grade = _calculate_course_grade(group)
        gpa_point = score_to_gpa4(final_grade) if final_grade is not None else 0.0

        results.append({
            "student_id": student_id,
            "student_code": student_code,
            "student_name": student_name,
            "course_id": course_id,
            "course_code": course_code,
            "course_name": course_name,
            "credits": credits,
            "semester_id": sem_id,
            "semester_name": sem_name,
            "final_grade": final_grade,
            "gpa_points": gpa_point,
        })

    return pd.DataFrame(results)


def calculate_gpa(student_id, semester_id=None):
    """
    Calculate weighted GPA for a student (credit-weighted average of GPA points).
    Returns dict with gpa, total_credits, courses_count.
    """
    df = get_student_course_grades(semester_id)
    if df.empty:
        return {"gpa": 0.0, "total_credits": 0, "courses_count": 0}

    student_df = df[df["student_id"] == student_id]
    if student_df.empty:
        return {"gpa": 0.0, "total_credits": 0, "courses_count": 0}

    weighted_sum = (student_df["gpa_points"] * student_df["credits"]).sum()
    total_credits = student_df["credits"].sum()

    gpa = round(weighted_sum / total_credits, 2) if total_credits > 0 else 0.0

    return {
        "gpa": gpa,
        "total_credits": int(total_credits),
        "courses_count": len(student_df),
    }


def class_rankings(semester_id=None):
    """
    Return students ranked by GPA (descending).
    Returns list of dicts: [{student_id, student_name, student_code, gpa, rank}, ...]
    """
    df = get_student_course_grades(semester_id)
    if df.empty:
        return []

    # Calculate GPA per student
    rankings = []
    for student_id in df["student_id"].unique():
        student_df = df[df["student_id"] == student_id]
        student_name = student_df.iloc[0]["student_name"]
        student_code = student_df.iloc[0]["student_code"]

        weighted_sum = (student_df["gpa_points"] * student_df["credits"]).sum()
        total_credits = student_df["credits"].sum()
        gpa = round(weighted_sum / total_credits, 2) if total_credits > 0 else 0.0

        avg_score = round(student_df["final_grade"].mean(), 2) if not student_df["final_grade"].isna().all() else 0.0

        rankings.append({
            "student_id": student_id,
            "student_name": student_name,
            "student_code": student_code,
            "gpa": gpa,
            "avg_score": avg_score,
            "total_credits": int(total_credits),
        })

    # Sort by GPA descending
    rankings.sort(key=lambda x: x["gpa"], reverse=True)

    # Assign ranks
    for i, r in enumerate(rankings, 1):
        r["rank"] = i

    return rankings


def at_risk_students(semester_id=None, threshold=2.0):
    """Return students with GPA below the threshold."""
    rankings = class_rankings(semester_id)
    return list(filter(lambda r: r["gpa"] < threshold, rankings))


def get_all_grades_flat(semester_id=None):
    """Return all final grades as a flat list for histogram plotting."""
    df = get_student_course_grades(semester_id)
    if df.empty:
        return []
    return df["final_grade"].dropna().tolist()


def get_student_semester_gpas(student_id):
    """Return GPA per semester for trend line plotting."""
    with get_connection() as conn:
        semesters = conn.execute("SELECT * FROM Semesters ORDER BY id").fetchall()

    trend = []
    for sem in semesters:
        gpa_info = calculate_gpa(student_id, sem["id"])
        trend.append({
            "semester_id": sem["id"],
            "semester_name": sem["name"],
            "gpa": gpa_info["gpa"],
        })
    return trend


def get_student_performance_radar(student_id, semester_id=None):
    """
    Get performance metrics for radar chart:
    [Assignment Avg, Midterm Avg, Final Avg, Attendance Rate, GPA]
    """
    df = _load_grade_data(semester_id)
    if df.empty:
        return None

    student_df = df[df["student_id"] == student_id]
    if student_df.empty:
        return None

    # Average by assignment type
    assignment_avg = student_df[student_df["assignment_type"] == "assignment"]["score"].mean()
    midterm_avg = student_df[student_df["assignment_type"] == "midterm"]["score"].mean()
    final_avg = student_df[student_df["assignment_type"] == "final"]["score"].mean()

    # Attendance rate
    with get_connection() as conn:
        query = """
            SELECT a.status, COUNT(*) as cnt
            FROM Attendance a
            JOIN Enrollments e ON a.enrollment_id = e.id
            WHERE e.student_id = ?
        """
        params = [student_id]
        if semester_id:
            query += " AND e.course_id IN (SELECT id FROM Courses WHERE semester_id = ?)"
            params.append(semester_id)
        query += " GROUP BY a.status"
        attendance = conn.execute(query, params).fetchall()

    total_sessions = sum(r["cnt"] for r in attendance)
    present = sum(r["cnt"] for r in attendance if r["status"] in ("present", "late"))
    attendance_rate = round((present / total_sessions) * 100, 1) if total_sessions > 0 else 0

    gpa_info = calculate_gpa(student_id, semester_id)

    return {
        "labels": ["Assignments", "Midterm", "Final Exam", "Attendance", "GPA (×25)"],
        "values": [
            round(assignment_avg, 1) if pd.notna(assignment_avg) else 0,
            round(midterm_avg, 1) if pd.notna(midterm_avg) else 0,
            round(final_avg, 1) if pd.notna(final_avg) else 0,
            attendance_rate,
            round(gpa_info["gpa"] * 25, 1),  # Scale GPA to 0-100 range for radar
        ],
    }
