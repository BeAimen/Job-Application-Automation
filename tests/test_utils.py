import pytest
from datetime import datetime, timedelta
import pytz

from src.utils import (
    generate_id, validate_email, substitute_placeholders,
    calculate_next_followup, is_followup_due,
    get_default_company, get_default_position
)
from src.config import DEFAULTS, TIMEZONE


def test_generate_id():
    """Test UUID generation."""
    id1 = generate_id()
    id2 = generate_id()

    assert id1 != id2
    assert len(id1) == 36  # UUID4 format


def test_validate_email():
    """Test email validation."""
    assert validate_email("test@example.com") is True
    assert validate_email("user.name@domain.co.uk") is True
    assert validate_email("invalid.email") is False
    assert validate_email("@example.com") is False
    assert validate_email("test@") is False


def test_substitute_placeholders():
    """Test placeholder substitution in email body."""
    body = "Dear [Company], I'm interested in [Position]."

    # With company name
    result = substitute_placeholders(body, "ACME Corp", "Engineer", "en")
    assert "ACME Corp" in result
    assert "Engineer" in result
    assert "[Company]" not in result

    # Without company name → should use language default
    placeholder_en = DEFAULTS["en"]["company_placeholder"]
    result = substitute_placeholders(body, None, "Engineer", "en")
    assert placeholder_en in result
    assert "[Company]" not in result

    # French version
    placeholder_fr = DEFAULTS["fr"]["company_placeholder"]
    result = substitute_placeholders(body, "", "Ingénieur", "fr")
    assert placeholder_fr in result
    assert "Ingénieur" in result


def test_calculate_next_followup():
    """Test follow-up date calculation."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    sent_date = now.isoformat()

    next_date = calculate_next_followup(sent_date, days=7)
    next_dt = datetime.fromisoformat(next_date)

    # Ensure timezone-aware
    if next_dt.tzinfo is None:
        next_dt = tz.localize(next_dt)

    diff = next_dt - now

    # Should be approximately 7 days
    assert timedelta(days=6) <= diff <= timedelta(days=8)


def test_is_followup_due():
    """Test follow-up due check."""
    tz = pytz.timezone(TIMEZONE)

    past_date = (datetime.now(tz) - timedelta(days=1)).isoformat()
    assert is_followup_due(past_date) is True

    future_date = (datetime.now(tz) + timedelta(days=1)).isoformat()
    assert is_followup_due(future_date) is False

    assert is_followup_due("invalid") is False


def test_get_defaults():
    """Test default getters."""
    assert get_default_company("en") == DEFAULTS["en"]["company_unknown"]
    assert get_default_company("fr") == DEFAULTS["fr"]["company_unknown"]

    assert get_default_position("en") == DEFAULTS["en"]["position"]
    assert get_default_position("fr") == DEFAULTS["fr"]["position"]
