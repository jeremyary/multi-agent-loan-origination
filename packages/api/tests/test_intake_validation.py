# This project was developed with assistance from AI tools.
"""Tests for intake field validation (S-2-F3-02, S-2-F3-03)."""

from src.services.intake_validation import (
    validate_credit_score,
    validate_dob,
    validate_email,
    validate_employment_status,
    validate_field,
    validate_income,
    validate_loan_amount,
    validate_loan_type,
    validate_property_value,
    validate_ssn,
)


class TestSSN:
    def test_valid_with_dashes(self):
        ok, _, val = validate_ssn("078-05-1120")
        assert ok and val == "078-05-1120"

    def test_valid_digits_only(self):
        ok, _, val = validate_ssn("078051120")
        assert ok and val == "078-05-1120"

    def test_rejects_short(self):
        ok, msg, _ = validate_ssn("12345")
        assert not ok and "9 digits" in msg

    def test_rejects_all_zeros(self):
        ok, _, _ = validate_ssn("000000000")
        assert not ok

    def test_rejects_sequential(self):
        ok, _, _ = validate_ssn("123456789")
        assert not ok


class TestDOB:
    def test_yyyy_mm_dd(self):
        ok, _, val = validate_dob("1990-06-15")
        assert ok and val == "1990-06-15"

    def test_mm_dd_yyyy(self):
        ok, _, val = validate_dob("06/15/1990")
        assert ok and val == "1990-06-15"

    def test_rejects_minor(self):
        ok, msg, _ = validate_dob("2020-01-01")
        assert not ok and "18" in msg

    def test_rejects_invalid_format(self):
        ok, _, _ = validate_dob("not-a-date")
        assert not ok


class TestEmail:
    def test_valid(self):
        ok, _, val = validate_email("test@example.com")
        assert ok and val == "test@example.com"

    def test_normalizes_case(self):
        ok, _, val = validate_email("TEST@Example.COM")
        assert ok and val == "test@example.com"

    def test_rejects_no_at(self):
        ok, _, _ = validate_email("not-an-email")
        assert not ok


class TestIncome:
    def test_plain_number(self):
        ok, _, val = validate_income("6250")
        assert ok and val == "6250.00"

    def test_with_dollar_and_comma(self):
        ok, _, val = validate_income("$6,250")
        assert ok and val == "6250.00"

    def test_rejects_negative(self):
        ok, _, _ = validate_income("-1000")
        assert not ok

    def test_rejects_absurd(self):
        ok, msg, _ = validate_income("5000000")
        assert not ok and "unusually high" in msg


class TestLoanAmount:
    def test_valid(self):
        ok, _, val = validate_loan_amount("350000")
        assert ok and val == "350000.00"

    def test_rejects_zero(self):
        ok, _, _ = validate_loan_amount("0")
        assert not ok

    def test_rejects_over_max(self):
        ok, _, _ = validate_loan_amount("200000000")
        assert not ok


class TestPropertyValue:
    def test_valid(self):
        ok, _, val = validate_property_value("$450,000")
        assert ok and val == "450000.00"

    def test_rejects_negative(self):
        ok, _, _ = validate_property_value("-100")
        assert not ok


class TestCreditScore:
    def test_valid(self):
        ok, _, val = validate_credit_score("750")
        assert ok and val == "750"

    def test_rejects_below_300(self):
        ok, _, _ = validate_credit_score("200")
        assert not ok

    def test_rejects_above_850(self):
        ok, _, _ = validate_credit_score("900")
        assert not ok

    def test_rejects_non_numeric(self):
        ok, _, _ = validate_credit_score("excellent")
        assert not ok


class TestLoanType:
    def test_exact_value(self):
        ok, _, val = validate_loan_type("fha")
        assert ok and val == "fha"

    def test_alias_conventional(self):
        ok, _, val = validate_loan_type("conventional")
        assert ok and val == "conventional_30"

    def test_rejects_unknown(self):
        ok, msg, _ = validate_loan_type("ninja_loan")
        assert not ok and "Valid" in msg


class TestEmploymentStatus:
    def test_exact_value(self):
        ok, _, val = validate_employment_status("self_employed")
        assert ok and val == "self_employed"

    def test_alias_w2(self):
        ok, _, val = validate_employment_status("w2")
        assert ok and val == "w2_employee"

    def test_alias_1099(self):
        ok, _, val = validate_employment_status("1099")
        assert ok and val == "self_employed"

    def test_rejects_unknown(self):
        ok, _, _ = validate_employment_status("astronaut")
        assert not ok


class TestDispatcher:
    def test_known_field(self):
        ok, _, val = validate_field("credit_score", "720")
        assert ok and val == "720"

    def test_unknown_field_passes_through(self):
        ok, _, val = validate_field("favorite_color", "blue")
        assert ok and val == "blue"
