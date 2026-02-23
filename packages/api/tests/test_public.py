# This project was developed with assistance from AI tools.
"""Tests for public API endpoints (products + affordability calculator)."""


def test_products_endpoint(client):
    response = client.get("/api/public/products")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_affordability_happy_path(client):
    """Standard calculation with reasonable inputs."""
    response = client.post("/api/public/calculate-affordability", json={
        "gross_annual_income": 80000,
        "monthly_debts": 500,
        "down_payment": 50000,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["max_loan_amount"] > 0
    assert data["estimated_monthly_payment"] > 0
    assert data["estimated_purchase_price"] > data["max_loan_amount"]
    assert data["dti_ratio"] > 0
    assert data["dti_warning"] is None


def test_affordability_debts_exceed_capacity(client):
    """When debts already exceed 43% of income, max loan should be 0."""
    response = client.post("/api/public/calculate-affordability", json={
        "gross_annual_income": 36000,
        "monthly_debts": 2000,
        "down_payment": 5000,
    })
    data = response.json()
    assert data["max_loan_amount"] == 0
    assert data["estimated_monthly_payment"] == 0
    assert data["dti_warning"] is not None


def test_affordability_low_down_payment_pmi_warning(client):
    """Down payment < 3% of purchase price should trigger PMI warning."""
    response = client.post("/api/public/calculate-affordability", json={
        "gross_annual_income": 120000,
        "monthly_debts": 200,
        "down_payment": 1000,
    })
    data = response.json()
    assert data["pmi_warning"] is not None
    assert "PMI" in data["pmi_warning"]


def test_affordability_rejects_negative_income(client):
    """Negative income should fail validation."""
    response = client.post("/api/public/calculate-affordability", json={
        "gross_annual_income": -50000,
        "monthly_debts": 500,
        "down_payment": 10000,
    })
    assert response.status_code == 422
