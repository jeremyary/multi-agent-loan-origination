# This project was developed with assistance from AI tools.
"""
Demo fixture data for Summit Cap Financial.

All fixture data is defined as Python dicts so enums can be referenced directly
and type-checked. Keycloak user IDs are deterministic UUIDs that match the
"id" fields in config/keycloak/summit-cap-realm.json.

Simulated for demonstration purposes -- not real financial data.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from db.enums import (
    ApplicationStage,
    ConditionSeverity,
    ConditionStatus,
    DecisionType,
    DocumentStatus,
    DocumentType,
    LoanType,
)

# ---------------------------------------------------------------------------
# Keycloak user references (deterministic UUIDs)
# ---------------------------------------------------------------------------
# These UUIDs match the "id" fields in config/keycloak/summit-cap-realm.json.
# Keycloak's JWT "sub" claim returns the user ID, and the application service
# filters by borrower.keycloak_user_id == sub. Using fixed IDs ensures the
# seeded data links correctly to authenticated users.

SARAH_MITCHELL_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567801"
JAMES_TORRES_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567802"
MARIA_CHEN_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567803"
DAVID_PARK_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567804"
ADMIN_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567805"

# Co-borrower (spouse of Sarah Mitchell)
JENNIFER_MITCHELL_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567806"

# Fictional borrowers (not in Keycloak -- only used for historical loan data)
MICHAEL_JOHNSON_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567811"
EMILY_RODRIGUEZ_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567812"
ROBERT_KIM_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567813"
LISA_WASHINGTON_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567814"
THOMAS_NGUYEN_ID = "d1a2b3c4-e5f6-7890-abcd-ef1234567815"


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC)


def _days_ago(n: int) -> datetime:
    return _NOW - timedelta(days=n)


def _days_from_now(n: int) -> datetime:
    return _NOW + timedelta(days=n)


# ---------------------------------------------------------------------------
# Borrower profiles
# ---------------------------------------------------------------------------

BORROWERS: list[dict] = [
    {
        "keycloak_user_id": SARAH_MITCHELL_ID,
        "first_name": "Sarah",
        "last_name": "Mitchell",
        "email": "sarah.mitchell@example.com",
        "ssn": "ENC:293-84-1567",
        "dob": datetime(1988, 6, 15, tzinfo=UTC),
    },
    {
        "keycloak_user_id": JENNIFER_MITCHELL_ID,
        "first_name": "Jennifer",
        "last_name": "Mitchell",
        "email": "jennifer.mitchell@example.com",
        "ssn": "ENC:384-71-2956",
        "dob": datetime(1990, 2, 8, tzinfo=UTC),
    },
    {
        "keycloak_user_id": "d1a2b3c4-e5f6-7890-abcd-ef1234567811",
        "first_name": "Michael",
        "last_name": "Johnson",
        "email": "michael.johnson@example.com",
        "ssn": "ENC:481-22-9034",
        "dob": datetime(1975, 11, 3, tzinfo=UTC),
    },
    {
        "keycloak_user_id": "d1a2b3c4-e5f6-7890-abcd-ef1234567812",
        "first_name": "Emily",
        "last_name": "Rodriguez",
        "email": "emily.rodriguez@example.com",
        "ssn": "ENC:612-50-3478",
        "dob": datetime(1992, 3, 22, tzinfo=UTC),
    },
    {
        "keycloak_user_id": "d1a2b3c4-e5f6-7890-abcd-ef1234567813",
        "first_name": "Robert",
        "last_name": "Kim",
        "email": "robert.kim@example.com",
        "ssn": "ENC:754-13-8821",
        "dob": datetime(1983, 9, 8, tzinfo=UTC),
    },
    {
        "keycloak_user_id": "d1a2b3c4-e5f6-7890-abcd-ef1234567814",
        "first_name": "Lisa",
        "last_name": "Washington",
        "email": "lisa.washington@example.com",
        "ssn": "ENC:328-67-4190",
        "dob": datetime(1990, 1, 27, tzinfo=UTC),
    },
    {
        "keycloak_user_id": "d1a2b3c4-e5f6-7890-abcd-ef1234567815",
        "first_name": "Thomas",
        "last_name": "Nguyen",
        "email": "thomas.nguyen@example.com",
        "ssn": "ENC:519-41-7763",
        "dob": datetime(1979, 7, 14, tzinfo=UTC),
    },
]

# ---------------------------------------------------------------------------
# Active applications (8) -- assigned to james.torres (loan officer)
# ---------------------------------------------------------------------------

# borrower_ref is the keycloak_user_id of the borrower; the seeder resolves
# it to the borrower.id FK at insert time.

ACTIVE_APPLICATIONS: list[dict] = [
    # --- 3 in APPLICATION stage ---
    {
        "borrower_ref": SARAH_MITCHELL_ID,
        "co_borrower_refs": [JENNIFER_MITCHELL_ID],
        "stage": ApplicationStage.APPLICATION,
        "loan_type": LoanType.CONVENTIONAL_30,
        "property_address": "1234 Elm Street, Denver, CO 80203",
        "loan_amount": Decimal("320000.00"),
        "property_value": Decimal("400000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(14),
        "financials": {
            "gross_monthly_income": Decimal("8500.00"),
            "monthly_debts": Decimal("2400.00"),
            "total_assets": Decimal("95000.00"),
            "credit_score": 742,
            "dti_ratio": 0.282,
        },
        "documents": [
            {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.BANK_STATEMENT, "status": DocumentStatus.PENDING_REVIEW},
        ],
    },
    {
        "borrower_ref": EMILY_RODRIGUEZ_ID,
        "stage": ApplicationStage.APPLICATION,
        "loan_type": LoanType.FHA,
        "property_address": "5678 Oak Avenue, Aurora, CO 80012",
        "loan_amount": Decimal("245000.00"),
        "property_value": Decimal("275000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(10),
        "financials": {
            "gross_monthly_income": Decimal("6200.00"),
            "monthly_debts": Decimal("1800.00"),
            "total_assets": Decimal("42000.00"),
            "credit_score": 688,
            "dti_ratio": 0.290,
        },
        "documents": [
            {"doc_type": DocumentType.W2, "status": DocumentStatus.UPLOADED},
            {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
        ],
    },
    {
        "borrower_ref": SARAH_MITCHELL_ID,
        "stage": ApplicationStage.APPLICATION,
        "loan_type": LoanType.CONVENTIONAL_15,
        "property_address": "910 Pine Lane, Lakewood, CO 80226",
        "loan_amount": Decimal("200000.00"),
        "property_value": Decimal("260000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(7),
        "financials": {
            "gross_monthly_income": Decimal("8500.00"),
            "monthly_debts": Decimal("2400.00"),
            "total_assets": Decimal("95000.00"),
            "credit_score": 742,
            "dti_ratio": 0.282,
        },
        "documents": [
            {
                "doc_type": DocumentType.PAY_STUB,
                "status": DocumentStatus.FLAGGED_FOR_RESUBMISSION,
                "quality_flags": json.dumps(["partially_illegible"]),
            },
        ],
    },
    # --- 2 in UNDERWRITING stage ---
    {
        "borrower_ref": ROBERT_KIM_ID,
        "stage": ApplicationStage.UNDERWRITING,
        "loan_type": LoanType.CONVENTIONAL_30,
        "property_address": "2345 Birch Court, Boulder, CO 80301",
        "loan_amount": Decimal("475000.00"),
        "property_value": Decimal("550000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(28),
        "financials": {
            "gross_monthly_income": Decimal("12000.00"),
            "monthly_debts": Decimal("3200.00"),
            "total_assets": Decimal("185000.00"),
            "credit_score": 765,
            "dti_ratio": 0.267,
        },
        "documents": [
            {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.BANK_STATEMENT, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
        ],
        "conditions": [
            {
                "description": "Verify employment with current employer",
                "severity": ConditionSeverity.PRIOR_TO_APPROVAL,
                "status": ConditionStatus.OPEN,
                "issued_by": MARIA_CHEN_ID,
            },
            {
                "description": "Provide most recent two months bank statements",
                "severity": ConditionSeverity.PRIOR_TO_APPROVAL,
                "status": ConditionStatus.RESPONDED,
                "issued_by": MARIA_CHEN_ID,
            },
        ],
    },
    {
        "borrower_ref": LISA_WASHINGTON_ID,
        "stage": ApplicationStage.UNDERWRITING,
        "loan_type": LoanType.VA,
        "property_address": "6789 Maple Drive, Fort Collins, CO 80525",
        "loan_amount": Decimal("380000.00"),
        "property_value": Decimal("410000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(21),
        "financials": {
            "gross_monthly_income": Decimal("9800.00"),
            "monthly_debts": Decimal("2900.00"),
            "total_assets": Decimal("120000.00"),
            "credit_score": 710,
            "dti_ratio": 0.296,
        },
        "documents": [
            {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.BANK_STATEMENT, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
        ],
        "conditions": [
            {
                "description": "Certificate of Eligibility required for VA loan",
                "severity": ConditionSeverity.PRIOR_TO_APPROVAL,
                "status": ConditionStatus.OPEN,
                "issued_by": MARIA_CHEN_ID,
            },
            {
                "description": "Property appraisal must meet VA minimum requirements",
                "severity": ConditionSeverity.PRIOR_TO_DOCS,
                "status": ConditionStatus.OPEN,
                "issued_by": MARIA_CHEN_ID,
            },
            {
                "description": "Verify no outstanding federal debts",
                "severity": ConditionSeverity.PRIOR_TO_APPROVAL,
                "status": ConditionStatus.CLEARED,
                "issued_by": MARIA_CHEN_ID,
                "cleared_by": MARIA_CHEN_ID,
            },
        ],
    },
    # --- 2 in CONDITIONAL_APPROVAL stage ---
    {
        "borrower_ref": MICHAEL_JOHNSON_ID,
        "co_borrower_refs": [EMILY_RODRIGUEZ_ID],
        "stage": ApplicationStage.CONDITIONAL_APPROVAL,
        "loan_type": LoanType.JUMBO,
        "property_address": "3456 Cedar Boulevard, Cherry Hills Village, CO 80113",
        "loan_amount": Decimal("650000.00"),
        "property_value": Decimal("820000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(42),
        "financials": {
            "gross_monthly_income": Decimal("18000.00"),
            "monthly_debts": Decimal("5400.00"),
            "total_assets": Decimal("450000.00"),
            "credit_score": 780,
            "dti_ratio": 0.300,
        },
        "documents": [
            {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.BANK_STATEMENT, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.TAX_RETURN, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
        ],
        "conditions": [
            {
                "description": "Final title insurance commitment required",
                "severity": ConditionSeverity.PRIOR_TO_CLOSING,
                "status": ConditionStatus.OPEN,
                "issued_by": MARIA_CHEN_ID,
            },
            {
                "description": "Hazard insurance binder with mortgagee clause",
                "severity": ConditionSeverity.PRIOR_TO_CLOSING,
                "status": ConditionStatus.CLEARED,
                "issued_by": MARIA_CHEN_ID,
                "cleared_by": MARIA_CHEN_ID,
            },
        ],
        "decisions": [
            {
                "decision_type": DecisionType.CONDITIONAL_APPROVAL,
                "rationale": "Strong financials and credit history. Conditions for "
                "title and insurance must be satisfied before closing.",
                "decided_by": MARIA_CHEN_ID,
            },
        ],
        "rate_lock": {
            "locked_rate": 6.875,
            "lock_date": _days_ago(10),
            "expiration_date": _days_from_now(35),
            "is_active": True,
        },
    },
    {
        "borrower_ref": THOMAS_NGUYEN_ID,
        "stage": ApplicationStage.CONDITIONAL_APPROVAL,
        "loan_type": LoanType.CONVENTIONAL_30,
        "property_address": "7890 Spruce Way, Centennial, CO 80112",
        "loan_amount": Decimal("350000.00"),
        "property_value": Decimal("425000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(35),
        "financials": {
            "gross_monthly_income": Decimal("10500.00"),
            "monthly_debts": Decimal("3150.00"),
            "total_assets": Decimal("160000.00"),
            "credit_score": 725,
            "dti_ratio": 0.300,
        },
        "documents": [
            {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.BANK_STATEMENT, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
        ],
        "conditions": [
            {
                "description": "Updated pay stub within 30 days of closing",
                "severity": ConditionSeverity.PRIOR_TO_DOCS,
                "status": ConditionStatus.RESPONDED,
                "issued_by": MARIA_CHEN_ID,
            },
            {
                "description": "Flood zone determination certificate",
                "severity": ConditionSeverity.PRIOR_TO_CLOSING,
                "status": ConditionStatus.CLEARED,
                "issued_by": MARIA_CHEN_ID,
                "cleared_by": JAMES_TORRES_ID,
            },
        ],
        "decisions": [
            {
                "decision_type": DecisionType.CONDITIONAL_APPROVAL,
                "rationale": "Acceptable risk profile. Standard conditions apply.",
                "decided_by": MARIA_CHEN_ID,
            },
        ],
        "rate_lock": {
            "locked_rate": 7.125,
            "lock_date": _days_ago(5),
            "expiration_date": _days_from_now(40),
            "is_active": True,
        },
    },
    # --- 1 in CLEAR_TO_CLOSE stage ---
    {
        "borrower_ref": SARAH_MITCHELL_ID,
        "stage": ApplicationStage.CLEAR_TO_CLOSE,
        "loan_type": LoanType.CONVENTIONAL_30,
        "property_address": "4567 Aspen Ridge, Highlands Ranch, CO 80129",
        "loan_amount": Decimal("425000.00"),
        "property_value": Decimal("510000.00"),
        "assigned_to": JAMES_TORRES_ID,
        "created_at": _days_ago(60),
        "financials": {
            "gross_monthly_income": Decimal("8500.00"),
            "monthly_debts": Decimal("2400.00"),
            "total_assets": Decimal("95000.00"),
            "credit_score": 742,
            "dti_ratio": 0.282,
        },
        "documents": [
            {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.BANK_STATEMENT, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.TAX_RETURN, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.PROPERTY_APPRAISAL, "status": DocumentStatus.ACCEPTED},
            {"doc_type": DocumentType.INSURANCE, "status": DocumentStatus.ACCEPTED},
        ],
        "conditions": [
            {
                "description": "Verify employment prior to closing",
                "severity": ConditionSeverity.PRIOR_TO_CLOSING,
                "status": ConditionStatus.CLEARED,
                "issued_by": MARIA_CHEN_ID,
                "cleared_by": MARIA_CHEN_ID,
            },
            {
                "description": "Title insurance commitment",
                "severity": ConditionSeverity.PRIOR_TO_CLOSING,
                "status": ConditionStatus.CLEARED,
                "issued_by": MARIA_CHEN_ID,
                "cleared_by": JAMES_TORRES_ID,
            },
            {
                "description": "Final loan disclosure signed",
                "severity": ConditionSeverity.PRIOR_TO_FUNDING,
                "status": ConditionStatus.CLEARED,
                "issued_by": MARIA_CHEN_ID,
                "cleared_by": JAMES_TORRES_ID,
            },
        ],
        "decisions": [
            {
                "decision_type": DecisionType.APPROVED,
                "rationale": "All conditions cleared. Borrower meets all underwriting "
                "requirements. Clear to close.",
                "decided_by": MARIA_CHEN_ID,
            },
        ],
        "rate_lock": {
            "locked_rate": 6.750,
            "lock_date": _days_ago(20),
            "expiration_date": _days_from_now(25),
            "is_active": True,
        },
    },
]


# ---------------------------------------------------------------------------
# Historical (closed) loans -- 20 total: 16 approved, 4 denied
# ---------------------------------------------------------------------------

_HISTORICAL_ADDRESSES = [
    "100 Main Street, Denver, CO 80202",
    "225 Market Ave, Denver, CO 80205",
    "340 Broadway, Boulder, CO 80302",
    "455 Pearl Street, Boulder, CO 80302",
    "570 College Ave, Fort Collins, CO 80524",
    "685 Mountain View Dr, Colorado Springs, CO 80903",
    "790 Tejon Street, Colorado Springs, CO 80903",
    "815 Nevada Ave, Colorado Springs, CO 80903",
    "930 Platte River Dr, Littleton, CO 80120",
    "1045 Wadsworth Blvd, Lakewood, CO 80214",
    "1160 Federal Blvd, Denver, CO 80204",
    "1275 Colfax Ave, Denver, CO 80218",
    "1390 Lincoln St, Denver, CO 80203",
    "1505 Grant St, Denver, CO 80203",
    "1620 Sherman St, Denver, CO 80203",
    "1735 Logan St, Denver, CO 80203",
    "1850 Washington St, Denver, CO 80203",
    "1965 Clarkson St, Denver, CO 80218",
    "2080 Downing St, Denver, CO 80205",
    "2195 York St, Denver, CO 80205",
]

# Borrower refs cycle through the fictional borrowers for historical loans
_HISTORICAL_BORROWER_REFS = [
    MICHAEL_JOHNSON_ID,
    EMILY_RODRIGUEZ_ID,
    ROBERT_KIM_ID,
    LISA_WASHINGTON_ID,
    THOMAS_NGUYEN_ID,
]

HISTORICAL_LOANS: list[dict] = []

# 16 approved historical loans
for i in range(16):
    _borrower_ref = _HISTORICAL_BORROWER_REFS[i % len(_HISTORICAL_BORROWER_REFS)]
    _loan_types = [
        LoanType.CONVENTIONAL_30,
        LoanType.CONVENTIONAL_15,
        LoanType.FHA,
        LoanType.VA,
        LoanType.JUMBO,
    ]
    _created = _days_ago(180 - (i * 10))
    _loan_amount = Decimal(str(200000 + i * 25000))
    _property_value = _loan_amount + Decimal(str(50000 + i * 5000))
    _credit_scores = [
        720,
        695,
        755,
        710,
        740,
        680,
        760,
        730,
        705,
        750,
        690,
        735,
        745,
        715,
        770,
        725,
    ]

    HISTORICAL_LOANS.append(
        {
            "borrower_ref": _borrower_ref,
            "stage": ApplicationStage.CLOSED,
            "loan_type": _loan_types[i % len(_loan_types)],
            "property_address": _HISTORICAL_ADDRESSES[i],
            "loan_amount": _loan_amount,
            "property_value": _property_value,
            "assigned_to": JAMES_TORRES_ID,
            "created_at": _created,
            "financials": {
                "gross_monthly_income": Decimal(str(7000 + i * 500)),
                "monthly_debts": Decimal(str(1800 + i * 100)),
                "total_assets": Decimal(str(50000 + i * 10000)),
                "credit_score": _credit_scores[i],
                "dti_ratio": round(0.25 + (i % 8) * 0.02, 3),
            },
            "documents": [
                {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
                {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
                {"doc_type": DocumentType.BANK_STATEMENT, "status": DocumentStatus.ACCEPTED},
                {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
            ],
            "decisions": [
                {
                    "decision_type": DecisionType.APPROVED,
                    "rationale": "Meets all underwriting criteria. Loan approved.",
                    "decided_by": MARIA_CHEN_ID,
                    "created_at": _created + timedelta(days=30),
                },
            ],
            "rate_lock": {
                "locked_rate": round(6.5 + (i % 10) * 0.125, 3),
                "lock_date": _created + timedelta(days=20),
                "expiration_date": _created + timedelta(days=65),
                "is_active": False,
            },
        }
    )

# 4 denied historical loans
_DENIAL_REASONS = [
    "Debt-to-income ratio exceeds 43% threshold. Monthly obligations are disproportionate to income.",
    "Credit score of 612 falls below minimum program requirement of 620.",
    "Insufficient documented income to support requested loan amount.",
    "Property appraisal came in significantly below purchase price. LTV exceeds program limits.",
]

for i in range(4):
    _borrower_ref = _HISTORICAL_BORROWER_REFS[i % len(_HISTORICAL_BORROWER_REFS)]
    _idx = 16 + i
    _created = _days_ago(150 - (i * 15))
    _loan_amount = Decimal(str(250000 + i * 30000))
    _property_value = _loan_amount + Decimal(str(30000 + i * 5000))
    _denied_credit_scores = [612, 648, 655, 632]

    HISTORICAL_LOANS.append(
        {
            "borrower_ref": _borrower_ref,
            "stage": ApplicationStage.DENIED,
            "loan_type": LoanType.CONVENTIONAL_30,
            "property_address": _HISTORICAL_ADDRESSES[_idx],
            "loan_amount": _loan_amount,
            "property_value": _property_value,
            "assigned_to": JAMES_TORRES_ID,
            "created_at": _created,
            "financials": {
                "gross_monthly_income": Decimal(str(5500 + i * 300)),
                "monthly_debts": Decimal(str(2500 + i * 200)),
                "total_assets": Decimal(str(15000 + i * 5000)),
                "credit_score": _denied_credit_scores[i],
                "dti_ratio": round(0.42 + i * 0.02, 3),
            },
            "documents": [
                {"doc_type": DocumentType.W2, "status": DocumentStatus.ACCEPTED},
                {"doc_type": DocumentType.PAY_STUB, "status": DocumentStatus.ACCEPTED},
                {"doc_type": DocumentType.ID, "status": DocumentStatus.ACCEPTED},
            ],
            "decisions": [
                {
                    "decision_type": DecisionType.DENIED,
                    "rationale": _DENIAL_REASONS[i],
                    "decided_by": MARIA_CHEN_ID,
                    "created_at": _created + timedelta(days=25),
                },
            ],
        }
    )


# ---------------------------------------------------------------------------
# HMDA demographics -- one per application (28 total: 8 active + 20 historical)
# ---------------------------------------------------------------------------

# Distribution: ~40% White, ~20% Black, ~15% Hispanic, ~15% Asian, ~10% Other
# Sex: ~50% Male, ~45% Female, ~5% prefer not to say
# These are applied in order to all applications (active first, then historical)

_RACE_DIST = (
    ["White"] * 11
    + ["Black or African American"] * 6
    + ["Asian"] * 4
    + ["Native Hawaiian or Other Pacific Islander"] * 2
    + ["American Indian or Alaska Native"] * 2
    + ["Two or More Races"] * 3
)

_ETHNICITY_DIST = ["Not Hispanic or Latino"] * 24 + ["Hispanic or Latino"] * 4

_SEX_DIST = ["Male"] * 14 + ["Female"] * 13 + ["Prefer not to say"] * 1

_AGE_DIST = ["25-34"] * 8 + ["35-44"] * 10 + ["45-54"] * 6 + ["55-64"] * 4

HMDA_DEMOGRAPHICS: list[dict] = []
for i in range(28):
    HMDA_DEMOGRAPHICS.append(
        {
            "application_index": i,  # resolved at seed time to actual application_id
            "race": _RACE_DIST[i % len(_RACE_DIST)],
            "ethnicity": _ETHNICITY_DIST[i % len(_ETHNICITY_DIST)],
            "sex": _SEX_DIST[i % len(_SEX_DIST)],
            "age": _AGE_DIST[i % len(_AGE_DIST)],
            "collection_method": "self_reported",
        }
    )


# ---------------------------------------------------------------------------
# Config hash -- deterministic hash of fixture content for manifest comparison
# ---------------------------------------------------------------------------


def compute_config_hash() -> str:
    """Compute a SHA-256 hash of the fixture data for idempotency checks."""
    content = json.dumps(
        {
            "borrower_count": len(BORROWERS),
            "active_count": len(ACTIVE_APPLICATIONS),
            "historical_count": len(HISTORICAL_LOANS),
            "hmda_count": len(HMDA_DEMOGRAPHICS),
            "borrower_ids": [b["keycloak_user_id"] for b in BORROWERS],
            "co_borrower_apps": sum(1 for a in ACTIVE_APPLICATIONS if a.get("co_borrower_refs")),
        },
        sort_keys=True,
    )
    return hashlib.sha256(content.encode()).hexdigest()
