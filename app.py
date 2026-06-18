"""
TEC004/05 - University Performance Tracker
Flask application entry point — full proposal integration (SP1–SP7).
"""
import os
import time
import json
import csv
import io
from flask import (
    Flask, render_template, request, session, redirect, url_for,
    flash, jsonify, send_file, abort,
)

import config
from database.schema import init_db, seed_data
from database.connection import execute_query
from models.person import Student, Instructor
from models.course import Course
from analytics.engine import (
    class_rankings, at_risk_students, get_all_grades_flat,
    calculate_gpa, get_student_course_grades,
    get_student_semester_gpas, get_student_performance_radar,
    pass_fail_rates, correlation_analysis, course_difficulty_stats,
)
from analytics.predictor import predictor
from visualization.charts import (
    grade_distribution_histogram, gpa_trend_line,
    performance_radar, ranking_bar_chart,
    course_difficulty_bar, grade_box_plot,
)
from pipeline.importer import batch_import
from pipeline.exporter import (
    export_grades_json, export_grades_csv, export_rankings_json, get_export_dir,
)
from crawler import execute_adaptive_crawl, sync_crawl_to_normalized
from auth.decorators import require_role, login_required, set_session_role

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

init_db()
seed_data()
predictor.train()


def get_semesters():
    return execute_query("SELECT * FROM Semesters ORDER BY id", fetchall=True)


def _semester_label(semester_id):
    if semester_id:
        sem = execute_query("SELECT name FROM Semesters WHERE id=?", (semester_id,), fetchone=True)
        return sem["name"] if sem else "Unknown"
    return "All Semesters"


def _student_scope_id():
    """Students may only view their own record (user_id maps to student id=1 for demo)."""
    if session.get("user_role") == "student":
        return session.get("user_id", 1)
    return None


# ─── DASHBOARD ───────────────────────────────────────────────
@app.route("/")
@login_required
@require_role("admin", "instructor", "student")
def dashboard():
    semester_id = request.args.get("semester_id", type=int)
    semesters = get_semesters()
    cache_bust = str(int(time.time()))
    semester_label = _semester_label(semester_id)

    rankings_data = class_rankings(semester_id)
    scope_id = _student_scope_id()
    if scope_id:
        rankings_data = [r for r in rankings_data if r["student_id"] == scope_id]

    total_students = len(rankings_data) if scope_id else execute_query(
        "SELECT COUNT(*) as c FROM Students", fetchone=True
    )["c"]
    if semester_id:
        total_courses = execute_query(
            "SELECT COUNT(*) as c FROM Courses WHERE semester_id=?", (semester_id,), fetchone=True
        )["c"]
    else:
        total_courses = execute_query("SELECT COUNT(*) as c FROM Courses", fetchone=True)["c"]

    avg_gpa = sum(r["gpa"] for r in rankings_data) / len(rankings_data) if rankings_data else 0
    at_risk = at_risk_students(semester_id)
    if scope_id:
        at_risk = [r for r in at_risk if r["student_id"] == scope_id]

    pf = pass_fail_rates(semester_id)
    ml_at_risk = predictor.ml_at_risk_students(semester_id=semester_id)
    if scope_id:
        ml_at_risk = [a for a in ml_at_risk if a["student_id"] == scope_id]

    grades = get_all_grades_flat(semester_id)
    stats = {
        "total_students": total_students,
        "total_courses": total_courses,
        "avg_gpa": avg_gpa,
        "at_risk_count": len(at_risk),
        "avg_score": sum(grades) / len(grades) if grades else 0,
        "pass_rate": pf["pass_rate"],
        "ml_at_risk_count": len(ml_at_risk),
    }

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
        ml_at_risk=ml_at_risk,
        charts={"histogram": hist_file, "rankings": rank_file},
        cache_bust=cache_bust,
    )


# ─── ANALYTICS (SP4) ─────────────────────────────────────────
@app.route("/analytics")
@login_required
@require_role("admin", "instructor")
def analytics_page():
    semester_id = request.args.get("semester_id", type=int)
    semesters = get_semesters()
    cache_bust = str(int(time.time()))
    semester_label = _semester_label(semester_id)

    pf = pass_fail_rates(semester_id)
    correlations = correlation_analysis(semester_id)
    course_stats = course_difficulty_stats(semester_id)
    grades = get_all_grades_flat(semester_id)

    box_file = grade_box_plot(grades, semester_label, f"box_{semester_id or 'all'}.png")
    diff_file = course_difficulty_bar(course_stats, semester_label, f"diff_{semester_id or 'all'}.png")

    return render_template(
        "analytics.html",
        active_page="analytics",
        semesters=semesters,
        current_semester=semester_id,
        semester_label=semester_label,
        pass_fail=pf,
        correlations=correlations,
        course_stats=course_stats,
        charts={"boxplot": box_file, "difficulty": diff_file},
        cache_bust=cache_bust,
    )


# ─── STUDENTS ────────────────────────────────────────────────
@app.route("/students")
@login_required
@require_role("admin", "instructor", "student")
def students_page():
    student_id = request.args.get("student_id", type=int)
    semester_id = request.args.get("semester_id", type=int)
    semesters = get_semesters()
    cache_bust = str(int(time.time()))

    scope_id = _student_scope_id()
    if scope_id:
        student_id = scope_id

    students = Student.all()
    if scope_id:
        students = [s for s in students if s.id == scope_id]

    selected_student = None
    gpa_info = {"gpa": 0, "total_credits": 0, "courses_count": 0}
    course_grades = []
    charts = {"trend": "empty.png", "radar": "empty.png"}

    if student_id:
        selected_student = Student.from_db(student_id)
        if selected_student:
            gpa_info = calculate_gpa(student_id, semester_id)
            df = get_student_course_grades(semester_id)
            if not df.empty:
                course_grades = df[df["student_id"] == student_id].to_dict("records")
            trend_file = gpa_trend_line(
                get_student_semester_gpas(student_id), selected_student.name, f"trend_{student_id}.png"
            )
            radar_file = performance_radar(
                get_student_performance_radar(student_id, semester_id),
                selected_student.name, f"radar_{student_id}.png",
            )
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
@login_required
@require_role("admin", "instructor", "student")
def courses_page():
    semester_id = request.args.get("semester_id", type=int)
    semesters = get_semesters()
    semester_label = _semester_label(semester_id)
    course_objects = Course.all(semester_id)

    courses = []
    for c in course_objects:
        instructor = Instructor.from_db(c.instructor_id) if c.instructor_id else None
        courses.append({
            "id": c.id,
            "course_code": c.course_code,
            "name": c.name,
            "credits": c.credits,
            "semester_name": c.get_semester_name(),
            "instructor_name": instructor.name if instructor else "TBD",
            "enrolled_count": len(c.get_enrolled_students()),
        })

    return render_template(
        "courses.html",
        active_page="courses",
        semesters=semesters,
        current_semester=semester_id,
        semester_label=semester_label,
        courses=courses,
    )


# ─── AI PREDICTION (SP6) ─────────────────────────────────────
@app.route("/prediction", methods=["GET", "POST"])
@login_required
@require_role("admin", "instructor", "student")
def prediction_page():
    scope_id = _student_scope_id()
    students = Student.all()
    if scope_id:
        students = [s for s in students if s.id == scope_id]

    courses_all = Course.all()
    courses = [{"id": c.id, "course_code": c.course_code, "name": c.name} for c in courses_all]

    prediction = None
    selected_student_id = None
    selected_course_id = None

    if request.method == "POST":
        selected_student_id = request.form.get("student_id", type=int)
        selected_course_id = request.form.get("course_id", type=int)
        if scope_id and selected_student_id != scope_id:
            abort(403)
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


# ─── DATA IMPORT / EXPORT (SP2) ──────────────────────────────
@app.route("/import", methods=["GET", "POST"])
@login_required
@require_role("admin", "instructor")
def import_page():
    results = None
    if request.method == "POST":
        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            flash("No files selected.", "danger")
        else:
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
                for p in saved_paths:
                    os.remove(p)
                predictor.train()
                flash(f"Imported {sum(f.get('imported', 0) for f in results['files'])} grades.", "success")

    return render_template("import.html", active_page="import", results=results)


@app.route("/export/grades.json")
@login_required
@require_role("admin", "instructor")
def export_grades_json_route():
    semester_id = request.args.get("semester_id", type=int)
    payload = export_grades_json(semester_id)
    buf = io.BytesIO(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    return send_file(buf, mimetype="application/json", as_attachment=True,
                     download_name="grades_export.json")


@app.route("/export/grades.csv")
@login_required
@require_role("admin", "instructor")
def export_grades_csv_route():
    semester_id = request.args.get("semester_id", type=int)
    rows = export_grades_csv(semester_id)
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    mem = io.BytesIO(buf.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True,
                     download_name="grades_export.csv")


@app.route("/export/rankings.json")
@login_required
@require_role("admin", "instructor")
def export_rankings_json_route():
    semester_id = request.args.get("semester_id", type=int)
    payload = export_rankings_json(semester_id)
    buf = io.BytesIO(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    return send_file(buf, mimetype="application/json", as_attachment=True,
                     download_name="rankings_export.json")


# ─── ADAPTIVE WEB CRAWL ────────────────────────────────────────
@app.route("/api/refresh-data", methods=["GET"])
@login_required
@require_role("admin", "instructor")
def refresh_data():
    try:
        crawled_data, data_source, source_label = execute_adaptive_crawl()
        records_synced = sync_crawl_to_normalized(crawled_data) if crawled_data else 0
        if records_synced:
            predictor.train()
        return jsonify({
            "status": "success",
            "data_source": data_source,
            "source_label": source_label,
            "records_synced": records_synced,
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─── LOGIN (SP7 — Selenium test target) ─────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "student")
        name = request.form.get("name", "User")
        user_id = 1 if role == "student" else None
        set_session_role(role, user_id=user_id, user_name=name)
        flash(f"Signed in as {name} ({role}).", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", config.PORT))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
