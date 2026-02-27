# This project was developed with assistance from AI tools.
"""Compliance check functions for ECOA, ATR/QM, and TRID.

Pure functions -- no DB calls, fully testable with plain values.
Each check returns a ComplianceCheckResult with regulation name,
status, rationale, and detail items.
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime


class ComplianceStatus(str, enum.Enum):
    """Severity-ordered compliance check status."""

    PASS = "PASS"
    CONDITIONAL_PASS = "CONDITIONAL_PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


# Severity ordering for worst-of comparison (higher = worse).
_STATUS_ORDER = {
    ComplianceStatus.PASS: 0,
    ComplianceStatus.CONDITIONAL_PASS: 1,
    ComplianceStatus.WARNING: 2,
    ComplianceStatus.FAIL: 3,
}


@dataclass
class ComplianceCheckResult:
    """Result of a single compliance check."""

    regulation: str
    status: ComplianceStatus
    rationale: str
    details: list[str] = field(default_factory=list)


def _worst_status(*statuses: ComplianceStatus) -> ComplianceStatus:
    """Return the most severe status from the given values."""
    return max(statuses, key=lambda s: _STATUS_ORDER[s])


# ---------------------------------------------------------------------------
# Business-day helper
# ---------------------------------------------------------------------------


def _business_days_between(start: datetime, end: datetime) -> int:
    """Count weekday days between start and end (exclusive of start, inclusive of end).

    Holidays are out of scope for MVP.
    """
    if end <= start:
        return 0
    count = 0
    current = start
    from datetime import timedelta

    one_day = timedelta(days=1)
    while current < end:
        current += one_day
        if current.weekday() < 5:  # Mon-Fri
            count += 1
    return count


# ---------------------------------------------------------------------------
# ECOA check
# ---------------------------------------------------------------------------


def check_ecoa(has_demographic_query: bool = False) -> ComplianceCheckResult:
    """Check ECOA compliance (Equal Credit Opportunity Act).

    ECOA prohibits discrimination based on protected characteristics.
    The architecture enforces this by isolating HMDA demographic data
    in a separate schema inaccessible to underwriting queries.

    Args:
        has_demographic_query: True if a demographic data query was
            attempted and refused during this underwriting session.
    """
    if has_demographic_query:
        return ComplianceCheckResult(
            regulation="ECOA",
            status=ComplianceStatus.WARNING,
            rationale="Demographic data query attempted and refused.",
            details=[
                "A query for protected demographic data was blocked by schema isolation.",
                "Decision must be based on financial factors only.",
            ],
        )
    return ComplianceCheckResult(
        regulation="ECOA",
        status=ComplianceStatus.PASS,
        rationale=(
            "No protected characteristics accessible. Decision based on financial factors only."
        ),
        details=["HMDA demographic data isolated in separate schema."],
    )


# ---------------------------------------------------------------------------
# ATR/QM check
# ---------------------------------------------------------------------------


def check_atr_qm(
    dti: float | None,
    has_income_docs: bool,
    has_asset_docs: bool,
    has_employment_docs: bool,
) -> ComplianceCheckResult:
    """Check ATR/QM compliance (Ability-to-Repay / Qualified Mortgage).

    Evaluates debt-to-income ratio and documentation completeness
    against ATR/QM standards.

    Args:
        dti: Debt-to-income ratio as a decimal (e.g. 0.38 for 38%).
            None if income data is missing.
        has_income_docs: Whether income documentation (W2/pay stub/tax return) exists.
        has_asset_docs: Whether asset documentation (bank statement) exists.
        has_employment_docs: Whether employment documentation (W2/pay stub) exists.
    """
    details: list[str] = []

    # Check documentation completeness
    if not has_income_docs:
        details.append("Missing income documentation (W2, pay stub, or tax return).")
    if not has_asset_docs:
        details.append("Missing asset documentation (bank statement).")
    if not has_employment_docs:
        details.append("Missing employment documentation (W2 or pay stub).")

    if dti is None:
        return ComplianceCheckResult(
            regulation="ATR/QM",
            status=ComplianceStatus.FAIL,
            rationale="DTI cannot be computed -- income data missing.",
            details=details or ["No financial data available to compute DTI."],
        )

    if dti > 0.50:
        details.insert(0, f"DTI ratio {dti:.1%} exceeds 50% maximum.")
        return ComplianceCheckResult(
            regulation="ATR/QM",
            status=ComplianceStatus.FAIL,
            rationale="Exceeds 50% DTI -- does not meet ATR standards.",
            details=details,
        )

    if 0.43 < dti <= 0.50:
        details.insert(
            0,
            f"DTI ratio {dti:.1%} exceeds QM safe harbor (43%) "
            "but may qualify under rebuttable presumption.",
        )
        status = ComplianceStatus.CONDITIONAL_PASS
        rationale = "Exceeds QM safe harbor, may qualify under rebuttable presumption."
    elif dti <= 0.43:
        if not has_income_docs or not has_asset_docs or not has_employment_docs:
            details.insert(0, f"DTI ratio {dti:.1%} within QM safe harbor.")
            status = ComplianceStatus.WARNING
            rationale = "DTI within limits but documentation is incomplete."
        else:
            details.insert(0, f"DTI ratio {dti:.1%} within QM safe harbor (43%).")
            status = ComplianceStatus.PASS
            rationale = "Meets QM safe harbor requirements."
    else:
        status = ComplianceStatus.PASS
        rationale = "Meets QM requirements."

    return ComplianceCheckResult(
        regulation="ATR/QM",
        status=status,
        rationale=rationale,
        details=details,
    )


# ---------------------------------------------------------------------------
# TRID check
# ---------------------------------------------------------------------------


def check_trid(
    le_delivery_date: datetime | None,
    app_created_at: datetime | None,
    cd_delivery_date: datetime | None,
    closing_date: datetime | None,
) -> ComplianceCheckResult:
    """Check TRID compliance (TILA-RESPA Integrated Disclosure).

    Validates disclosure timing requirements:
    - Loan Estimate (LE) must be delivered within 3 business days of application.
    - Closing Disclosure (CD) must be delivered at least 3 business days before closing.

    Args:
        le_delivery_date: When the Loan Estimate was delivered.
        app_created_at: When the application was created.
        cd_delivery_date: When the Closing Disclosure was delivered.
        closing_date: Scheduled closing date.
    """
    details: list[str] = []
    item_statuses: list[ComplianceStatus] = []

    # --- Loan Estimate timing ---
    if le_delivery_date is None:
        details.append("Loan Estimate: not yet delivered.")
        item_statuses.append(ComplianceStatus.WARNING)
    elif app_created_at is not None:
        bdays = _business_days_between(app_created_at, le_delivery_date)
        if bdays <= 3:
            details.append(f"Loan Estimate: delivered within {bdays} business day(s) -- on time.")
            item_statuses.append(ComplianceStatus.PASS)
        else:
            details.append(
                f"Loan Estimate: delivered after {bdays} business days -- "
                "exceeds 3 business day requirement."
            )
            item_statuses.append(ComplianceStatus.FAIL)
    else:
        details.append("Loan Estimate: application date unavailable for timing check.")
        item_statuses.append(ComplianceStatus.WARNING)

    # --- Closing Disclosure timing ---
    if closing_date is None:
        details.append("Closing Disclosure: no closing date scheduled -- timing N/A.")
        item_statuses.append(ComplianceStatus.PASS)
    elif cd_delivery_date is None:
        details.append("Closing Disclosure: closing scheduled but CD not yet delivered.")
        item_statuses.append(ComplianceStatus.WARNING)
    else:
        bdays = _business_days_between(cd_delivery_date, closing_date)
        if bdays >= 3:
            details.append(f"Closing Disclosure: {bdays} business days before closing -- on time.")
            item_statuses.append(ComplianceStatus.PASS)
        else:
            details.append(
                f"Closing Disclosure: only {bdays} business day(s) before closing -- "
                "must be at least 3 business days."
            )
            item_statuses.append(ComplianceStatus.FAIL)

    overall = _worst_status(*item_statuses) if item_statuses else ComplianceStatus.PASS

    rationale_map = {
        ComplianceStatus.PASS: "All TRID disclosure timing requirements met.",
        ComplianceStatus.CONDITIONAL_PASS: "TRID timing conditionally met.",
        ComplianceStatus.WARNING: "TRID timing incomplete -- disclosures pending.",
        ComplianceStatus.FAIL: "TRID timing violation -- disclosure deadline missed.",
    }

    return ComplianceCheckResult(
        regulation="TRID",
        status=overall,
        rationale=rationale_map[overall],
        details=details,
    )


# ---------------------------------------------------------------------------
# Combined runner
# ---------------------------------------------------------------------------


def run_all_checks(
    ecoa: ComplianceCheckResult,
    atr_qm: ComplianceCheckResult,
    trid: ComplianceCheckResult,
) -> dict:
    """Combine individual check results into an overall compliance summary.

    Returns:
        Dict with overall_status, checks list, and can_proceed flag.
        can_proceed is True unless any check FAILed.
    """
    checks = [ecoa, atr_qm, trid]
    overall = _worst_status(ecoa.status, atr_qm.status, trid.status)
    has_fail = any(c.status == ComplianceStatus.FAIL for c in checks)

    return {
        "overall_status": overall,
        "checks": checks,
        "can_proceed": not has_fail,
    }
