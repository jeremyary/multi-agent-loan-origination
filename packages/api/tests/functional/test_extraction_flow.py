# This project was developed with assistance from AI tools.
"""Functional tests: Document extraction pipeline flow.

Tests through the real FastAPI app with mocked LLM, S3, and DB.
Verifies:
- Upload triggers background processing dispatch
- Background task receives correct document ID
"""

from io import BytesIO

import pytest

from .data_factory import make_app_sarah_1
from .mock_db import make_upload_session
from .personas import borrower_sarah

pytestmark = pytest.mark.functional


def _post_upload(client, application_id=101, content_type="application/pdf", filename="test.pdf"):
    """Helper: POST a file to the upload endpoint."""
    data = b"%PDF-1.4 fake document content"
    return client.post(
        f"/api/applications/{application_id}/documents",
        files={"file": (filename, BytesIO(data), content_type)},
        data={"doc_type": "w2"},
    )


class TestUploadTriggersProcessing:
    """Upload triggers background extraction dispatch."""

    def test_upload_triggers_processing(self, make_upload_client):
        """Upload returns 201 with status=processing and dispatches background task."""
        app_obj = make_app_sarah_1()
        session = make_upload_session(application=app_obj)
        client, _mock_storage = make_upload_client(borrower_sarah(), session)

        resp = _post_upload(client, application_id=101)

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "processing"

        # Verify extraction was dispatched via fixture's exposed mock
        client._mock_create_task.assert_called_once()


class TestExtractionDispatchesCorrectDocId:
    """Background task receives the correct document ID."""

    def test_extraction_dispatched_with_doc_id(self, make_upload_client):
        """process_document is called with the newly created document's ID."""
        app_obj = make_app_sarah_1()
        session = make_upload_session(application=app_obj)
        client, _mock_storage = make_upload_client(borrower_sarah(), session)

        resp = _post_upload(client, application_id=101)

        assert resp.status_code == 201

        # The extraction service's process_document was called with the doc ID
        client._mock_extraction_svc.process_document.assert_called_once_with(501)

        # And that coroutine was passed to create_task
        client._mock_create_task.assert_called_once()
