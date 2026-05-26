"""
tests/test_ml.py
Tests for bed forecasting and readmission risk models.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["ENCRYPTION_KEY"] = "a" * 64


def test_bed_forecast_returns_list():
    from ml.bed_forecast import forecast_bed_demand
    results = forecast_bed_demand("ICU / Critical Care", periods=7)
    assert isinstance(results, list)
    assert len(results) == 7


def test_bed_forecast_fields():
    from ml.bed_forecast import forecast_bed_demand
    results = forecast_bed_demand("Cardiology", periods=3)
    for r in results:
        assert "department" in r
        assert "date" in r
        assert "predicted_occupancy" in r
        assert "lower_bound" in r
        assert "upper_bound" in r
        assert r["lower_bound"] <= r["predicted_occupancy"] <= r["upper_bound"] + 1  # allow floating point


def test_bed_forecast_unknown_dept():
    from ml.bed_forecast import forecast_bed_demand
    results = forecast_bed_demand("UnknownDept", periods=5)
    assert len(results) == 5


def test_readmission_risk_range():
    from ml.readmission_risk import score_readmission_risk
    result = score_readmission_risk(1, age=65, los_days=10, department="ICU / Critical Care", prev_admissions=2, icd_code="I21", is_emergency=True)
    assert 0 <= result["risk_score"] <= 100


def test_readmission_risk_levels():
    from ml.readmission_risk import score_readmission_risk
    low = score_readmission_risk(1, age=25, los_days=1, department="Paediatrics", prev_admissions=0)
    high = score_readmission_risk(2, age=80, los_days=20, department="ICU / Critical Care", prev_admissions=5, icd_code="I21", is_emergency=True)
    assert high["risk_score"] > low["risk_score"]
    assert high["risk_level"] in ["medium", "high"]
    assert low["risk_level"] in ["low", "medium"]


def test_readmission_has_factors():
    from ml.readmission_risk import score_readmission_risk
    result = score_readmission_risk(1, age=70, los_days=8, department="Cardiology", prev_admissions=1, icd_code="I10")
    assert len(result["top_factors"]) > 0
    assert "recommendation" in result
    assert len(result["recommendation"]) > 10


def test_readmission_shap_factors_have_required_fields():
    from ml.readmission_risk import score_readmission_risk
    result = score_readmission_risk(1, age=60, los_days=5, department="Oncology")
    for factor in result["top_factors"]:
        assert "factor" in factor
        assert "contribution" in factor
