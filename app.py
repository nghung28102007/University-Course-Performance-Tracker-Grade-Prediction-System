"""
TEC004/05 - University Performance Tracker
Flask application entry point.
"""
import os
import time
from flask import Flask, render_template, request, session, redirect, url_for, flash

import config
from database.schema import init_db, seed_data
from database.connection import execute_query
from models.person import Student, Instructor
from models.course import Course
from analytics.engine import (
    class_rankings, at_risk_students, get_all_grades_flat,
    calculate_gpa, get_student_course_grades,
    get_student_semester_gpas, get_student_performance_radar,
)
from analytics.predictor import predictor
from visualization.charts import (
    grade_distribution_histogram, gpa_trend_line,
    performance_radar, ranking_bar_chart,
)
from pipeline.importer import batch_import

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Initialize DB on startup
init_db()
seed_data()

# Train AI model on startup
predictor.train()


def get_semesters():
    """Fetch all semesters from the database (used by every page for tabs)."""
    return execute_query("SELECT * FROM Semesters ORDER BY id", fetchall=True)


@app.before_request
def set_default_session():
    """Set default admin session for demo."""
    if "user_role" not in session:
        session["user_role"] = "admin"
        session["user_name"] = "Hưng"
        session["user_id"] = 1


# ─── DASHBOARD ───────────────────────────────────────────────
@app.route("/")
def dashboard():
    semester_id = request.args.get("semester_id", type=int)
    semesters = get_semesters()
    cache_bust = str(int(time.time()))

    # Semester label
    if semester_id:
        sem = execute_query("SELECT name FROM Semesters WHERE id=?", (semester_id,), fetchone=True)
        semester_label = sem["name"] if sem else "Unknown"
    else:
        semester_label = "All Semesters"

    # Rankings
    rankings_data = class_rankings(semester_id)

    # Stats
    total_students = execute_query("SELECT COUNT(*) as c FROM Students", fetchone=True)["c"]
    if semester_id:
        total_courses = execute_query(
            "SELECT COUNT(*) as c FROM Courses WHERE semester_id=?", (semester_id,), fetchone=True
        )["c"]
    else:
        total_courses = execute_query("SELECT COUNT(*) as c FROM Courses", fetchone=True)["c"]

    avg_gpa = sum(r["gpa"] for r in rankings_data) / len(rankings_data) if rankings_data else 0
    at_risk = at_risk_students(semester_id)
    grades = get_all_grades_flat(semester_id)
    avg_score = sum(grades) / len(grades) if grades else 0

    stats = {
        "total_students": total_students,
        "total_courses": total_courses,
        "avg_gpa": avg_gpa,
        "at_risk_count": len(at_risk),
        "avg_score": avg_score,
    }

    # Generate charts
    hist_file = grade_distribution_histogram(grades, semester_label, f"hist_{semester_id or 'all'}.png")
    rank_file = ranking_bar_chart(rankings_data, semester_label, f"rank_{semester_id or 'all'}.png")

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        semesters=semesters,
        current_semester=semester_id,
        semester_label=semester_label,
        stats=stats,
        rankings=rankings_data,
        charts={"histogram": hist_file, "rankings": rank_file},
        cache_bust=cache_bust,
    )


# ─── STUDENTS ────────────────────────────────────────────────
@app.route("/students")
def students_page():
    student_id = request.args.get("student_id", type=int)
    semester_id = request.args.get("semester_id", type=int)
    semesters = get_semesters()
    students = Student.all()
    cache_bust = str(int(time.time()))

    selected_student = None
    gpa_info = {"gpa": 0, "total_credits": 0, "courses_count": 0}
    course_grades = []
    charts = {"trend": "empty.png", "radar": "empty.png"}

    if student_id:
        selected_student = Student.from_db(student_id)
        if selected_student:
            gpa_info = calculate_gpa(student_id, semester_id)

            # Course grades
            df = get_student_course_grades(semester_id)
            if not df.empty:
                sdf = df[df["student_id"] == student_id]
                course_grades = sdf.to_dict("records")

            # Generate charts
            trend_data = get_student_semester_gpas(student_id)
            trend_file = gpa_trend_line(trend_data, selected_student.name, f"trend_{student_id}.png")

            radar_data = get_student_performance_radar(student_id, semester_id)
            radar_file = performance_radar(radar_data, selected_student.name, f"radar_{student_id}.png")

            charts = {"trend": trend_file, "radar": radar_file}

    return render_template(
        "students.html",
        active_page="students",
        students=students,
        semesters=semesters,
        current_semester=semester_id,
        selected_student=selected_student,
        gpa_info=gpa_info,
        course_grades=course_grades,
        charts=charts,
        cache_bust=cache_bust,
    )


# ─── COURSES ─────────────────────────────────────────────────
@app.route("/courses")
def courses_page():
    semester_id = request.args.get("semester_id", type=int)
    semesters = get_semesters()

    if semester_id:
        sem = execute_query("SELECT name FROM Semesters WHERE id=?", (semester_id,), fetchone=True)
        semester_label = sem["name"] if sem else "Unknown"
    else:
        semester_label = "All Semesters"

    course_objects = Course.all(semester_id)

    courses = []
    for c in course_objects:
        instructor = Instructor.from_db(c.instructor_id) if c.instructor_id else None
        enrolled = c.get_enrolled_students()
        courses.append({
            "id": c.id,
            "course_code": c.course_code,
            "name": c.name,
            "credits": c.credits,
            "semester_name": c.get_semester_name(),
            "instructor_name": instructor.name if instructor else "TBD",
            "enrolled_count": len(enrolled),
        })

    return render_template(
        "courses.html",
        active_page="courses",
        semesters=semesters,
        current_semester=semester_id,
        semester_label=semester_label,
        courses=courses,
    )


# ─── AI PREDICTION ───────────────────────────────────────────
@app.route("/prediction", methods=["GET", "POST"])
def prediction_page():
    students = Student.all()
    courses_all = Course.all()
    courses = [{"id": c.id, "course_code": c.course_code, "name": c.name} for c in courses_all]

    prediction = None
    selected_student_id = None
    selected_course_id = None

    if request.method == "POST":
        selected_student_id = request.form.get("student_id", type=int)
        selected_course_id = request.form.get("course_id", type=int)

        if selected_student_id and selected_course_id:
            if not predictor.is_trained:
                predictor.train()
            prediction = predictor.predict_for_student(selected_student_id, selected_course_id)

    return render_template(
        "prediction.html",
        active_page="prediction",
        students=students,
        courses=courses,
        prediction=prediction,
        selected_student_id=selected_student_id,
        selected_course_id=selected_course_id,
        model_metrics=predictor.metrics if predictor.is_trained else None,
    )


# ─── DATA IMPORT ─────────────────────────────────────────────
@app.route("/import", methods=["GET", "POST"])
def import_page():
    results = None

    if request.method == "POST":
        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            flash("No files selected.", "danger")
        else:
            # Save uploaded files temporarily
            upload_dir = os.path.join(config.BASE_DIR, "data", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            saved_paths = []
            for f in files:
                if f.filename:
                    path = os.path.join(upload_dir, f.filename)
                    f.save(path)
                    saved_paths.append(path)

            if saved_paths:
                results = batch_import(saved_paths)
                # Clean up
                for p in saved_paths:
                    os.remove(p)

                total_imported = sum(f.get("imported", 0) for f in results["files"])
                flash(f"Imported {total_imported} grades from {len(saved_paths)} file(s).", "success")

    return render_template(
        "import.html",
        active_page="import",
        results=results,
    )


# ─── LOGIN (Simple demo) ────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "student")
        name = request.form.get("name", "User")
        session["user_role"] = role
        session["user_name"] = name
        return redirect(url_for("dashboard"))
    return render_template("base.html", active_page="login")


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=True)
