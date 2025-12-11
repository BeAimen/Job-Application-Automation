import uuid
import validators
from datetime import datetime, timedelta
from typing import Optional
import pytz

from src.config import TIMEZONE, FOLLOWUP_DAYS, DEFAULTS


# ---------------------------------------------------------
# ID GENERATION
# ---------------------------------------------------------
def generate_id() -> str:
    """Generate a unique UUID for application tracking."""
    return str(uuid.uuid4())


# ---------------------------------------------------------
# EMAIL VALIDATION
# ---------------------------------------------------------
def validate_email(email: str) -> bool:
    """Validate email address format."""
    return bool(validators.email(email))


# ---------------------------------------------------------
# TIMESTAMP HANDLING
# ---------------------------------------------------------
def get_current_timestamp() -> str:
    """Return current timestamp in ISO 8601 format with timezone."""
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).isoformat()


# ---------------------------------------------------------
# FOLLOW-UP DATE CALCULATION
# ---------------------------------------------------------
def calculate_next_followup(sent_date: str, days: int = FOLLOWUP_DAYS) -> str:
    """
    Calculate next follow-up date based on sent date.

    Args:
        sent_date: ISO format datetime string.
        days: Number of days to offset.

    Returns:
        ISO format datetime string for next follow-up.
    """
    tz = pytz.timezone(TIMEZONE)

    try:
        dt = datetime.fromisoformat(sent_date)

        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = tz.localize(dt)
    except Exception:
        dt = datetime.now(tz)

    next_date = dt + timedelta(days=days)
    return next_date.isoformat()


# ---------------------------------------------------------
# TEMPLATE PLACEHOLDER SYSTEM
# ---------------------------------------------------------
def substitute_placeholders(
    body: str,
    company: Optional[str],
    position: str,
    language: str
) -> str:
    """
    Replace placeholders in the email body template.

    Placeholders:
        [Company]
        [Position]

    Args:
        body: Email template.
        company: Company name or None.
        position: Position title.
        language: "en" or "fr".

    Returns:
        Processed body text.
    """
    # Replace [Position]
    body = body.replace("[Position]", position)

    # Replace [Company]
    if company and company.strip():
        body = body.replace("[Company]", company)
    else:
        body = body.replace("[Company]", DEFAULTS[language]["company_placeholder"])

    return body


# ---------------------------------------------------------
# DEFAULT FETCHERS
# ---------------------------------------------------------
def get_default_company(language: str) -> str:
    """Return default company name for the given language."""
    return DEFAULTS[language]["company_unknown"]


def get_default_position(language: str) -> str:
    """Return default position for the given language."""
    return DEFAULTS[language]["position"]


def get_default_body(language: str) -> str:
    """Return the default email template body for the language."""
    return DEFAULTS[language]["body"]


# ---------------------------------------------------------
# FOLLOW-UP DUE CHECK
# ---------------------------------------------------------
def is_followup_due(next_followup_date: str) -> bool:
    """
    Determine whether a follow-up is due.

    Args:
        next_followup_date: ISO formatted datetime string.

    Returns:
        True if follow-up is due, False otherwise.
    """
    tz = pytz.timezone(TIMEZONE)

    try:
        dt = datetime.fromisoformat(next_followup_date)

        # ensure timezone-aware
        if dt.tzinfo is None:
            dt = tz.localize(dt)

        now = datetime.now(tz)
        return now >= dt

    except Exception:
        return False
