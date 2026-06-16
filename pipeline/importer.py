"""
Data pipeline for batch importing CSV/JSON grade sheets.
Uses lambda, map, filter for data transformation.
Uses ThreadPoolExecutor for concurrent file processing.
"""
import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from database.connection import get_connection


def parse_csv(filepath):
    """
    Parse a CSV grade file. Expected columns:
    student_code, course_code, assignment_type, score
    
    Uses lambda/map/filter for row processing.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Validate required columns exist
    required = {"student_code", "course_code", "assignment_type", "score"}
    if rows and not required.issubset(rows[0].keys()):
        return {"error": f"Missing columns. Required: {required}", "rows": []}

    # Transform: strip whitespace, convert score to float
    clean = list(map(
        lambda r: {
            "student_code": r["student_code"].strip(),
            "course_code": r["course_code"].strip(),
            "assignment_type": r["assignment_type"].strip().lower(),
            "score": float(r["score"]),
        },
        rows,
    ))

    # Filter: remove invalid scores
    valid = list(filter(lambda r: 0 <= r["score"] <= 100, clean))
    invalid_count = len(clean) - len(valid)

    return {"rows": valid, "total": len(clean), "invalid": invalid_count}


def parse_json(filepath):
    """
    Parse a JSON grade file. Expected format:
    [{"student_code": "...", "course_code": "...", "assignment_type": "...", "score": ...}, ...]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return {"error": "JSON must be an array of objects", "rows": []}

    # Transform + filter using lambda/map/filter
    clean = list(map(
        lambda r: {
            "student_code": str(r.get("student_code", "")).strip(),
            "course_code": str(r.get("course_code", "")).strip(),
            "assignment_type": str(r.get("assignment_type", "")).strip().lower(),
            "score": float(r.get("score", -1)),
        },
        data,
    ))

    valid = list(filter(
        lambda r: r["student_code"] and r["course_code"] and 0 <= r["score"] <= 100,
        clean,
    ))

    return {"rows": valid, "total": len(clean), "invalid": len(clean) - len(valid)}


def import_grades(rows):
    """
    Import parsed grade rows into the database.
    Matches student_code → student_id, course_code → course_id → enrollment_id.
    """
    imported = 0
    errors = []

    with get_connection() as conn:
        for row in rows:
            try:
                # Find student
                student = conn.execute(
                    "SELECT id FROM Students WHERE student_code=?",
                    (row["student_code"],),
                ).fetchone()
                if not student:
                    errors.append(f"Student {row['student_code']} not found")
                    continue

                # Find course
                course = conn.execute(
                    "SELECT id FROM Courses WHERE course_code=?",
                    (row["course_code"],),
                ).fetchone()
                if not course:
                    errors.append(f"Course {row['course_code']} not found")
                    continue

                # Find enrollment
                enrollment = conn.execute(
                    "SELECT id FROM Enrollments WHERE student_id=? AND course_id=?",
                    (student["id"], course["id"]),
                ).fetchone()
                if not enrollment:
                    errors.append(f"No enrollment for {row['student_code']} in {row['course_code']}")
                    continue

                # Find assignment by type
                assignment = conn.execute(
                    "SELECT id FROM Assignments WHERE course_id=? AND type=?",
                    (course["id"], row["assignment_type"]),
                ).fetchone()
                if not assignment:
                    errors.append(f"No {row['assignment_type']} assignment for {row['course_code']}")
                    continue

                # Upsert grade
                conn.execute(
                    """INSERT INTO Grades (enrollment_id, assignment_id, score, graded_date)
                       VALUES (?, ?, ?, date('now'))
                       ON CONFLICT(enrollment_id, assignment_id) DO UPDATE SET score=?, graded_date=date('now')""",
                    (enrollment["id"], assignment["id"], row["score"], row["score"]),
                )
                imported += 1

            except Exception as e:
                errors.append(f"Error on row {row}: {str(e)}")

    return {"imported": imported, "errors": errors}


def process_file(filepath):
    """Process a single file (CSV or JSON) and import grades."""
    start = time.time()
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        result = parse_csv(filepath)
    elif ext == ".json":
        result = parse_json(filepath)
    else:
        return {"file": filepath, "error": f"Unsupported format: {ext}"}

    if "error" in result:
        return {"file": filepath, "error": result["error"]}

    import_result = import_grades(result["rows"])
    elapsed = round(time.time() - start, 3)

    return {
        "file": os.path.basename(filepath),
        "total_rows": result["total"],
        "invalid_rows": result["invalid"],
        "imported": import_result["imported"],
        "errors": import_result["errors"],
        "time_seconds": elapsed,
    }


def batch_import(filepaths):
    """
    Import multiple grade files concurrently using ThreadPoolExecutor.
    Returns a summary of all imports.
    """
    results = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_file, fp): fp for fp in filepaths}
        for future in as_completed(futures):
            results.append(future.result())

    total_time = round(time.time() - start, 3)
    return {"files": results, "total_time_seconds": total_time}
