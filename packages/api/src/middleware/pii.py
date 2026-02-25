# This project was developed with assistance from AI tools.
"""PII masking utilities for CEO role.

Masks sensitive fields in response data so that CEO-role users see
aggregate/metadata without individual PII. Masking failure returns 500
rather than leaking unmasked data.
"""

import re


def mask_ssn(value: str | None) -> str | None:
    """Mask SSN to ***-**-1234 format (last 4 visible)."""
    if value is None:
        return None
    # Extract last 4 digits from any format
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 4:
        return f"***-**-{digits[-4:]}"
    return "***-**-****"


def mask_dob(value: str | None) -> str | None:
    """Mask DOB to YYYY-**-** format (year visible only)."""
    if value is None:
        return None
    # Handle ISO datetime strings (2024-03-15T00:00:00)
    match = re.match(r"(\d{4})", str(value))
    if match:
        return f"{match.group(1)}-**-**"
    return "****-**-**"


def mask_account_number(value: str | None) -> str | None:
    """Mask account number to ****5678 format (last 4 visible)."""
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 4:
        return f"****{digits[-4:]}"
    return "********"


def mask_borrower_pii(borrower_dict: dict) -> dict:
    """Apply PII masking to a borrower dict for CEO-role responses."""
    masked = borrower_dict.copy()
    if "ssn_encrypted" in masked:
        masked["ssn_encrypted"] = mask_ssn(masked["ssn_encrypted"])
    if "dob" in masked:
        masked["dob"] = mask_dob(masked["dob"])
    return masked


def mask_application_pii(app_dict: dict) -> dict:
    """Apply PII masking to an application dict for CEO-role responses."""
    masked = app_dict.copy()
    if "borrowers" in masked:
        masked["borrowers"] = [mask_borrower_pii(b) for b in masked["borrowers"]]
    return masked
