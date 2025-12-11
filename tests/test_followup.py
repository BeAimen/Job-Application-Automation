import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
import pytz

from src.followup import FollowupEngine


@pytest.fixture
def mock_clients():
    """Create mock clients for sheets, mailer, and attachments."""
    sheets = Mock()
    mailer = Mock()
    attachments = Mock()
    return sheets, mailer, attachments


@pytest.fixture
def followup_engine(mock_clients):
    """Instantiate FollowupEngine using mock dependencies."""
    sheets, mailer, attachments = mock_clients
    return FollowupEngine(sheets, mailer, attachments)


# ---------------------------------------------------------
# CASE 1: No follow-ups due → no emails sent
# ---------------------------------------------------------
def test_process_followups_no_due(followup_engine, mock_clients):
    sheets, _, _ = mock_clients

    sheets.get_applications_for_followup.return_value = []  # no apps returned

    stats = followup_engine.process_followups("en", dry_run=True)

    assert stats["sent"] == 0
    assert stats["skipped"] == 0
    assert stats["failed"] == 0


# ---------------------------------------------------------
# CASE 2: Due follow-up → email sent successfully
# ---------------------------------------------------------
def test_process_followups_with_due(followup_engine, mock_clients):
    sheets, mailer, attachments = mock_clients

    tz = pytz.UTC
    past_date = (datetime.now(tz) - timedelta(days=1)).isoformat()

    due_app = {
        "id": "test-id",
        "email": "test@example.com",
        "position": "Engineer",
        "body": "Test body",
        "cv": "test_cv.pdf",
        "followups": 0,
        "next_followup_date": past_date,
        "company": "Test Corp",
        "sent_date": past_date,
        "status": "Sent",
        "phone": "",
        "website": "",
        "notes": ""
    }

    sheets.get_applications_for_followup.return_value = [due_app]

    # attachment exists
    attachments.get_attachment_path.return_value = Mock()

    # email send returns message ID
    mailer.send_with_delay.return_value = {"id": "msg-123"}

    # no bounce
    mailer.check_bounces.return_value = None

    stats = followup_engine.process_followups("en", dry_run=False)

    # EXPECTATIONS
    assert stats["sent"] == 1
    assert stats["failed"] == 0

    # Mailer was called
    mailer.send_with_delay.assert_called_once()

    # Application follow-up updated
    sheets.update_application_followup.assert_called_once()

    # Activity logged
    sheets.log_activity.assert_any_call(
        "test-id",
        "test@example.com",
        "followup_sent",
        "success",
        "Follow-up #1 sent"
    )


# ---------------------------------------------------------
# CASE 3: Attachment missing → follow-up skipped
# ---------------------------------------------------------
def test_process_followups_missing_attachment(followup_engine, mock_clients):
    sheets, mailer, attachments = mock_clients

    tz = pytz.UTC
    past_date = (datetime.now(tz) - timedelta(days=1)).isoformat()

    due_app = {
        "id": "test-id",
        "email": "test@example.com",
        "position": "Engineer",
        "body": "Test body",
        "cv": "missing.pdf",
        "followups": 0,
        "next_followup_date": past_date,
        "company": "Test Corp",
        "sent_date": past_date,
        "status": "Sent",
        "phone": "",
        "website": "",
        "notes": ""
    }

    sheets.get_applications_for_followup.return_value = [due_app]

    # Attachment does NOT exist
    attachments.get_attachment_path.return_value = None

    stats = followup_engine.process_followups("en", dry_run=False)

    assert stats["sent"] == 0
    assert stats["skipped"] == 1

    # Ensure email was NOT sent
    mailer.send_with_delay.assert_not_called()

    # Ensure skip was logged
    sheets.log_activity.assert_any_call(
        "test-id",
        "test@example.com",
        "followup_skipped",
        "failed",
        "Attachment not found: missing.pdf"
    )
