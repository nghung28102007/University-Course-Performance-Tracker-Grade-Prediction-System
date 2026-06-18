"""
SP2: Export grades and reports to CSV/JSON.
Uses lambda/map for record transformation.
"""
import csv
import json
import os
import time
from functools import reduce
from database.connection import get_connection
from analytics.engine import class_rankings, get_student_course_grades, pass_fail_rates
import config


def _grades_to_records(semester_id=None):
    """Build flat export records from analytics engine."""
    df = get_student_course_grades(semester_id)
    if df.empty:
        return []
    return df.to_dict("records")


def export_grades_json(semester_id=None, filepath=None):
    """Export all student course grades to JSON."""
    records = _grades_to_records(semester_id)
    payload = {
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "semester_id": semester_id,
        "total_records": len(records),
        "grades": list(map(
            lambda r: {
                "student_code": r["student_code"],
                "student_name": r["student_name"],
                "course_code": r["course_code"],
                "course_name": r["course_name"],
                "final_grade": r["final_grade"],
                "gpa_points": r["gpa_points"],
                "credits": r["credits"],
            },
            records,
        )),
    }
    if filepath:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


def export_grades_csv(semester_id=None, filepath=None):
    """Export all student course grades to CSV."""
    records = _grades_to_records(semester_id)
    fieldnames = ["student_code", "student_name", "course_code", "course_name",
                  "final_grade", "gpa_points", "credits", "semester_name"]
    rows = list(map(
        lambda r: {k: r.get(k, "") for k in fieldnames},
        records,
    ))
    if filepath:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return rows


def export_rankings_json(semester_id=None, filepath=None):
    """Export class rankings and pass/fail summary to JSON."""
    rankings = class_rankings(semester_id)
    rates = pass_fail_rates(semester_id)
    payload = {
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "semester_id": semester_id,
        "pass_fail_summary": rates,
        "rankings": rankings,
        "summary_gpa_avg": round(
            reduce(lambda acc, r: acc + r["gpa"], rankings, 0) / len(rankings), 2
        ) if rankings else 0.0,
    }
    if filepath:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


def get_export_dir():
    """Default export directory."""
    export_dir = os.path.join(config.BASE_DIR, "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir
