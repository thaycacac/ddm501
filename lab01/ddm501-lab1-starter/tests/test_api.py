"""
Tests for the Credit Default Risk Scoring API.

Run with:
    pytest tests/ -v
    pytest tests/ -v --cov=app --cov-report=term-missing
"""

import copy

import pytest
from fastapi.testclient import TestClient

from app.main import app

# A well-behaved applicant: always paid on time, low utilisation.
GOOD_APPLICANT = {
    "limit_bal": 300000,
    "sex": 2,
    "education": 1,
    "marriage": 2,
    "age": 38,
    "pay_status": [-1, -1, -1, -1, -1, -1],
    "bill_amt": [12000, 11500, 11000, 10500, 10000, 9500],
    "pay_amt": [12000, 11500, 11000, 10500, 10000, 9500],
}

# An applicant in trouble: months behind, near the limit, paying almost nothing.
RISKY_APPLICANT = {
    "limit_bal": 20000,
    "sex": 1,
    "education": 3,
    "marriage": 1,
    "age": 24,
    "pay_status": [4, 3, 3, 2, 2, 2],
    "bill_amt": [19800, 19500, 19000, 18500, 18000, 17500],
    "pay_amt": [0, 0, 200, 0, 300, 0],
}

RESPONSE_FIELDS = {
    "default_probability",
    "risk_band",
    "decision",
    "review_threshold",
    "decline_threshold",
    "model_version",
}


def _expected_decision(probability: float, review: float, decline: float) -> tuple[str, str]:
    if probability >= decline:
        return "HIGH", "DECLINE"
    if probability >= review:
        return "MEDIUM", "REVIEW"
    return "LOW", "APPROVE"


@pytest.fixture(scope="module")
def client():
    """Client bound to the app lifespan, so the model is actually loaded."""
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    """The /health endpoint."""

    def test_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/health").json()
        assert set(data) == {"status", "model_loaded", "model_version"}
        assert isinstance(data["model_loaded"], bool)

    def test_model_is_loaded(self, client):
        data = client.get("/health").json()
        assert data["model_loaded"] is True
        assert data["status"] == "healthy"


class TestInfoEndpoints:
    """The / and /model/info endpoints."""

    def test_root_returns_api_info(self, client):
        data = client.get("/").json()
        assert {"name", "version", "docs", "health"} <= set(data)

    def test_model_info_reports_metrics(self, client):
        data = client.get("/model/info").json()
        assert data["is_loaded"] is True
        assert 0.5 < data["metrics"]["roc_auc"] <= 1.0


class TestPredictEndpoint:
    """The /predict endpoint — happy path."""

    def test_valid_application_returns_200(self, client):
        response = client.post("/predict", json=GOOD_APPLICANT)
        assert response.status_code == 200

    def test_probability_is_a_valid_probability(self, client):
        data = client.post("/predict", json=GOOD_APPLICANT).json()
        assert 0.0 <= data["default_probability"] <= 1.0

    def test_response_contains_every_field(self, client):
        data = client.post("/predict", json=GOOD_APPLICANT).json()
        assert set(data) == RESPONSE_FIELDS

    def test_decision_is_consistent_with_thresholds(self, client):
        for applicant in (GOOD_APPLICANT, RISKY_APPLICANT):
            data = client.post("/predict", json=applicant).json()
            expected_band, expected_decision = _expected_decision(
                data["default_probability"],
                data["review_threshold"],
                data["decline_threshold"],
            )
            assert data["risk_band"] == expected_band
            assert data["decision"] == expected_decision

    def test_deterministic(self, client):
        first = client.post("/predict", json=GOOD_APPLICANT).json()
        second = client.post("/predict", json=GOOD_APPLICANT).json()
        assert first == second


class TestModelBehaviour:
    """Properties the model must satisfy."""

    def test_risky_scores_higher_than_good(self, client):
        good = client.post("/predict", json=GOOD_APPLICANT).json()
        risky = client.post("/predict", json=RISKY_APPLICANT).json()
        assert risky["default_probability"] > good["default_probability"]

    def test_more_delay_never_lowers_risk(self, client):
        mild = copy.deepcopy(GOOD_APPLICANT)
        severe = copy.deepcopy(GOOD_APPLICANT)
        mild["pay_status"] = [1, 0, 0, 0, 0, 0]
        severe["pay_status"] = [4, 3, 3, 2, 2, 2]
        mild_score = client.post("/predict", json=mild).json()["default_probability"]
        severe_score = client.post("/predict", json=severe).json()["default_probability"]
        assert severe_score >= mild_score


class TestValidation:
    """Bad input must fail at the edge."""

    @pytest.mark.parametrize(
        "field,value",
        [
            ("sex", 3),
            ("education", 9),
            ("marriage", 0),
            ("age", 12),
            ("age", 150),
            ("limit_bal", 0),
            ("limit_bal", -5000),
        ],
    )
    def test_out_of_range_value_is_rejected(self, client, field, value):
        payload = copy.deepcopy(GOOD_APPLICANT)
        payload[field] = value
        assert client.post("/predict", json=payload).status_code == 422

    def test_missing_field_is_rejected(self, client):
        payload = copy.deepcopy(GOOD_APPLICANT)
        del payload["age"]
        assert client.post("/predict", json=payload).status_code == 422

    def test_wrong_list_length_is_rejected(self, client):
        payload = copy.deepcopy(GOOD_APPLICANT)
        payload["pay_status"] = [0, 0, 0]
        assert client.post("/predict", json=payload).status_code == 422

    def test_pay_status_out_of_domain_is_rejected(self, client):
        payload = copy.deepcopy(GOOD_APPLICANT)
        payload["pay_status"] = [99, 0, 0, 0, 0, 0]
        assert client.post("/predict", json=payload).status_code == 422

    def test_negative_payment_is_rejected(self, client):
        payload = copy.deepcopy(GOOD_APPLICANT)
        payload["pay_amt"] = [12000, -1, 11000, 10500, 10000, 9500]
        assert client.post("/predict", json=payload).status_code == 422

    def test_empty_body_is_rejected(self, client):
        assert client.post("/predict", json={}).status_code == 422


class TestBatchEndpoint:
    """The /predict/batch endpoint."""

    def test_returns_one_result_per_application(self, client):
        payload = {"applications": [GOOD_APPLICANT, RISKY_APPLICANT, GOOD_APPLICANT]}
        data = client.post("/predict/batch", json=payload).json()
        assert data["total_count"] == 3
        assert len(data["predictions"]) == 3

    def test_order_is_preserved(self, client):
        payload = {"applications": [GOOD_APPLICANT, RISKY_APPLICANT]}
        data = client.post("/predict/batch", json=payload).json()
        assert (
            data["predictions"][1]["default_probability"]
            > data["predictions"][0]["default_probability"]
        )

    def test_matches_single_prediction(self, client):
        single = client.post("/predict", json=GOOD_APPLICANT).json()
        batch = client.post(
            "/predict/batch", json={"applications": [GOOD_APPLICANT]}
        ).json()
        assert batch["predictions"][0] == single

    def test_empty_batch_is_rejected(self, client):
        assert client.post("/predict/batch", json={"applications": []}).status_code == 422
