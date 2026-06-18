"""Core unit tests for TEC004/05 proposal deliverables."""
import os
import sys
import json
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db, seed_data
from models.gradebook import WeightedGrade, CurvedGrade, PassFailGrade, get_gradebook_for_course
from analytics.engine import calculate_gpa, class_rankings, pass_fail_rates, correlation_analysis
from analytics.predictor import PredictorModel
from pipeline.importer import parse_csv, parse_json
from pipeline.exporter import export_grades_json, export_rankings_json
from config import score_to_gpa4


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    seed_data()


# SP1 — OOP & Polymorphism
def test_gradebook_polymorphism():
    assert isinstance(get_gradebook_for_course("CS101"), WeightedGrade)
    assert isinstance(get_gradebook_for_course("MATH101"), CurvedGrade)
    assert isinstance(get_gradebook_for_course("SE101"), PassFailGrade)


def test_weighted_grade_calculation():
    gb = WeightedGrade()
    score = gb.calculate_final_grade(1)
    assert score is None or 0 <= score <= 100


# SP2 — File I/O
def test_csv_parse():
    sample = os.path.join(os.path.dirname(__file__), "..", "data", "sample_grades.csv")
    if os.path.exists(sample):
        result = parse_csv(sample)
        assert "rows" in result
        assert result["total"] >= 0


def test_json_export():
    payload = export_grades_json()
    assert "grades" in payload
    assert payload["total_records"] > 0


def test_rankings_export():
    payload = export_rankings_json()
    assert "rankings" in payload
    assert "pass_fail_summary" in payload


# SP3 — SQLite & GPA
def test_gpa_calculation():
    gpa_info = calculate_gpa(1)
    assert 0 <= gpa_info["gpa"] <= 4.0
    assert gpa_info["courses_count"] > 0


def test_class_rankings():
    rankings = class_rankings()
    assert len(rankings) == 8
    assert rankings[0]["rank"] == 1
    assert rankings[0]["gpa"] >= rankings[-1]["gpa"]


def test_score_to_gpa4():
    assert score_to_gpa4(95) == 4.0
    assert score_to_gpa4(50) == 1.3


# SP4 — Analytics
def test_pass_fail_rates():
    rates = pass_fail_rates()
    assert rates["total"] > 0
    assert abs(rates["pass_rate"] + rates["fail_rate"] - 100.0) < 0.2


def test_correlation_analysis():
    corr = correlation_analysis()
    assert isinstance(corr, dict)


# SP6 — ML Prediction
def test_predictor_train_and_predict():
    model = PredictorModel()
    metrics = model.train()
    assert model.is_trained
    assert "samples" in metrics
    result = model.predict(75, 80, 90)
    assert 0 <= result["predicted_final"] <= 100


def test_ml_at_risk_students():
    model = PredictorModel()
    model.train()
    alerts = model.ml_at_risk_students(predicted_threshold=100)
    assert isinstance(alerts, list)
