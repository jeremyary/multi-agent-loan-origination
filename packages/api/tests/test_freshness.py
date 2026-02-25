# This project was developed with assistance from AI tools.
"""Tests for document freshness validation."""

from datetime import date

from src.services.freshness import check_freshness


def test_pay_stub_fresh():
    """Pay stub within 30 days is fresh."""
    extractions = [{"field_name": "pay_period_end", "field_value": "2026-02-01"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result is None


def test_pay_stub_stale():
    """Pay stub older than 30 days gets wrong_period."""
    extractions = [{"field_name": "pay_period_end", "field_value": "2026-01-01"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result == "wrong_period"


def test_pay_stub_future_date():
    """Pay stub with future date gets future_date flag."""
    extractions = [{"field_name": "pay_period_end", "field_value": "2026-03-15"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result == "future_date"


def test_bank_statement_fresh():
    """Bank statement within 60 days is fresh."""
    extractions = [{"field_name": "statement_period_end", "field_value": "2026-01-15"}]
    result = check_freshness("bank_statement", extractions, reference_date=date(2026, 2, 20))
    assert result is None


def test_bank_statement_stale():
    """Bank statement older than 60 days gets wrong_period."""
    extractions = [{"field_name": "statement_period_end", "field_value": "2025-11-01"}]
    result = check_freshness("bank_statement", extractions, reference_date=date(2026, 2, 20))
    assert result == "wrong_period"


def test_no_threshold_for_w2():
    """W2 has no freshness threshold -- always returns None."""
    extractions = [{"field_name": "tax_year", "field_value": "2020"}]
    result = check_freshness("w2", extractions, reference_date=date(2026, 2, 20))
    assert result is None


def test_missing_date_field():
    """Missing date field returns None (can't determine freshness)."""
    extractions = [{"field_name": "gross_pay", "field_value": "5000"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result is None


def test_unparseable_date():
    """Unparseable date value returns None."""
    extractions = [{"field_name": "pay_period_end", "field_value": "not-a-date"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result is None


def test_slash_date_format():
    """Handles MM/DD/YYYY date format."""
    extractions = [{"field_name": "pay_period_end", "field_value": "02/10/2026"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result is None


def test_boundary_exactly_30_days():
    """Exactly 30 days old is still fresh (not stale)."""
    extractions = [{"field_name": "pay_period_end", "field_value": "2026-01-21"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result is None


def test_boundary_31_days():
    """31 days old is stale."""
    extractions = [{"field_name": "pay_period_end", "field_value": "2026-01-20"}]
    result = check_freshness("pay_stub", extractions, reference_date=date(2026, 2, 20))
    assert result == "wrong_period"
