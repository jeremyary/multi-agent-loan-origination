# This project was developed with assistance from AI tools.
"""PII masking middleware and utilities for CEO role.

Masks sensitive fields (SSN, DOB) in JSON response bodies when the
authenticated user's data scope has ``pii_mask=True``.  The middleware
runs after every response so new endpoints get automatic coverage without
per-route masking logic.

The ``request.state.pii_mask`` flag is set by the auth dependency
(``get_current_user`` in ``middleware/auth.py``).
"""

import json
import logging
import re
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Fields to mask and their masking functions
_PII_FIELD_MASKERS: dict[str, Any] = {}


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


# Register PII fields and their maskers
_PII_FIELD_MASKERS = {
    "ssn": mask_ssn,
    "dob": mask_dob,
    "account_number": mask_account_number,
}


def _mask_pii_recursive(obj: Any) -> Any:
    """Walk a JSON-compatible structure and mask known PII fields."""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            masker = _PII_FIELD_MASKERS.get(key)
            if masker and isinstance(value, str | None):
                result[key] = masker(value)
            else:
                result[key] = _mask_pii_recursive(value)
        return result
    if isinstance(obj, list):
        return [_mask_pii_recursive(item) for item in obj]
    return obj


def mask_borrower_pii(borrower_dict: dict) -> dict:
    """Apply PII masking to a borrower dict for CEO-role responses."""
    masked = borrower_dict.copy()
    if "ssn" in masked:
        masked["ssn"] = mask_ssn(masked["ssn"])
    if "dob" in masked:
        masked["dob"] = mask_dob(masked["dob"])
    return masked


def mask_application_pii(app_dict: dict) -> dict:
    """Apply PII masking to an application dict for CEO-role responses."""
    masked = app_dict.copy()
    if "borrowers" in masked:
        masked["borrowers"] = [mask_borrower_pii(b) for b in masked["borrowers"]]
    return masked


class PIIMaskingMiddleware(BaseHTTPMiddleware):
    """Intercept JSON responses and mask PII when ``request.state.pii_mask`` is set."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if not getattr(request.state, "pii_mask", False):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Read full body from the streaming response
        body_bytes = b""
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                body_bytes += chunk.encode("utf-8")
            else:
                body_bytes += chunk

        try:
            data = json.loads(body_bytes)
            masked = _mask_pii_recursive(data)
            new_body = json.dumps(masked).encode("utf-8")
        except (json.JSONDecodeError, TypeError):
            new_body = body_bytes

        return Response(
            content=new_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
