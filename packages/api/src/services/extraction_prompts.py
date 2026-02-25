# This project was developed with assistance from AI tools.
"""Document extraction prompt templates and field definitions.

Keeps prompt construction separate from the extraction service so prompts
can be reviewed and iterated on independently.
"""

EXTRACTION_FIELDS: dict[str, list[str]] = {
    "w2": [
        "employer_name",
        "employee_name",
        "tax_year",
        "wages",
        "federal_tax_withheld",
        "state_tax_withheld",
    ],
    "pay_stub": [
        "employer_name",
        "pay_period_start",
        "pay_period_end",
        "gross_pay",
        "net_pay",
        "ytd_gross_pay",
    ],
    "bank_statement": [
        "bank_name",
        "account_number_last4",
        "statement_period_start",
        "statement_period_end",
        "ending_balance",
        "average_balance",
    ],
    "tax_return": [
        "tax_year",
        "filing_status",
        "adjusted_gross_income",
        "total_tax",
        "taxable_income",
    ],
    "id": [
        "full_name",
        "date_of_birth",
        "id_number_last4",
        "expiration_date",
        "issuing_authority",
    ],
}

QUALITY_FLAGS = [
    "blurry",
    "incomplete",
    "wrong_period",
    "document_type_mismatch",
    "unsigned",
]

# HMDA demographic keywords for post-extraction filter
HMDA_KEYWORDS: set[str] = {
    "race",
    "ethnicity",
    "sex",
    "gender",
    "marital_status",
    "national_origin",
    "disability",
    "age_group",
}


def build_extraction_prompt(doc_type: str, text: str) -> list[dict]:
    """Build messages for text-based LLM extraction."""
    fields = EXTRACTION_FIELDS.get(doc_type, [])
    fields_csv = ", ".join(fields) if fields else "any relevant fields"

    system_msg = (
        "You are a document extraction assistant for a mortgage lending system. "
        "Extract structured data from the provided document text. "
        "Respond ONLY with valid JSON matching this schema:\n"
        "{\n"
        '  "extractions": [\n'
        '    {"field_name": "<name>", "field_value": "<value>", '
        '"confidence": <0.0-1.0>, "source_page": <int>}\n'
        "  ],\n"
        f'  "quality_flags": [<zero or more of: {", ".join(QUALITY_FLAGS)}>],\n'
        '  "detected_doc_type": "<actual document type detected>"\n'
        "}\n\n"
        f"Expected document type: {doc_type}\n"
        f"Expected fields: {fields_csv}\n"
        "IMPORTANT: If the document contains any demographic or government "
        "monitoring information (race, ethnicity, sex, gender, marital status, "
        "national origin), extract those fields as well.\n"
        "If a field is not found, omit it. Do not guess values."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"Extract data from this document:\n\n{text}"},
    ]


def build_image_extraction_prompt(doc_type: str) -> dict:
    """Build system message for image-based LLM extraction.

    The image content block is added separately by the caller.
    """
    fields = EXTRACTION_FIELDS.get(doc_type, [])
    fields_csv = ", ".join(fields) if fields else "any relevant fields"

    return {
        "role": "system",
        "content": (
            "You are a document extraction assistant for a mortgage lending system. "
            "Extract structured data from the provided document image. "
            "Respond ONLY with valid JSON matching this schema:\n"
            "{\n"
            '  "extractions": [\n'
            '    {"field_name": "<name>", "field_value": "<value>", '
            '"confidence": <0.0-1.0>, "source_page": <int>}\n'
            "  ],\n"
            f'  "quality_flags": [<zero or more of: {", ".join(QUALITY_FLAGS)}>],\n'
            '  "detected_doc_type": "<actual document type detected>"\n'
            "}\n\n"
            f"Expected document type: {doc_type}\n"
            f"Expected fields: {fields_csv}\n"
            "IMPORTANT: If the document contains any demographic or government "
            "monitoring information (race, ethnicity, sex, gender, marital status, "
            "national origin), extract those fields as well.\n"
            "If a field is not found, omit it. Do not guess values."
        ),
    }
