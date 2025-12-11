import base64
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional
import time
import random

import backoff
from googleapiclient.discovery import Resource

from src.config import GMAIL_USER_EMAIL, DEFAULT_DELAY_BETWEEN_EMAILS, MAX_RETRIES


class GmailMailer:
    """Gmail API wrapper for sending emails with optional attachments."""

    def __init__(self, service: Resource):
        self.service = service
        self.user_email = GMAIL_USER_EMAIL

    # ---------------------------------------------------------
    # EMAIL SENDING (WITH RETRIES)
    # ---------------------------------------------------------
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=MAX_RETRIES,
        giveup=lambda e: isinstance(e, ValueError)  # do not retry bad inputs
    )
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_path: Optional[Path] = None
    ) -> dict:
        """
        Send an email using Gmail API with an optional attachment.
        """

        # ----------- VALIDATION -----------
        if not to_email:
            raise ValueError("Recipient email is required.")
        if not subject.strip():
            raise ValueError("Email subject cannot be empty.")
        if not body.strip():
            raise ValueError("Email body cannot be empty.")

        # ----------- BASE MESSAGE -----------
        message = MIMEMultipart()
        message["to"] = to_email
        message["from"] = self.user_email
        message["subject"] = subject

        message.attach(MIMEText(body, "plain"))

        # ----------- ATTACHMENTS -----------
        if attachment_path:
            if not attachment_path.exists():
                raise ValueError(f"Attachment not found: {attachment_path}")

            mime_type, _ = mimetypes.guess_type(str(attachment_path))
            if mime_type:
                main_type, sub_type = mime_type.split("/")
            else:
                main_type, sub_type = "application", "octet-stream"

            with open(attachment_path, "rb") as f:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{attachment_path.name}"'
            )
            message.attach(part)

        # ----------- ENCODE MESSAGE FOR GMAIL -----------
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # ----------- SEND REQUEST -----------
        return self.service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

    # ---------------------------------------------------------
    # DELAYED SEND (ANTI-RATE LIMIT)
    # ---------------------------------------------------------
    def send_with_delay(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_path: Optional[Path] = None,
        delay: int = DEFAULT_DELAY_BETWEEN_EMAILS
    ) -> dict:
        """
        Send email with a random jitter delay to avoid Gmail throttling limits.
        """
        time.sleep(delay + random.uniform(0, 1))
        return self.send_email(to_email, subject, body, attachment_path)

    # ---------------------------------------------------------
    # BOUNCE CHECKING
    # ---------------------------------------------------------
    def check_bounces(self, message_id: str) -> Optional[dict]:
        """
        Check if Gmail marked a message as bounced.

        NOTE: Gmail does NOT provide a perfect API for bounce checking.
        This is heuristic-based.
        """

        try:
            message = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            headers = message.get("payload", {}).get("headers", [])

            bounce_indicators = [
                "x-failed-recipients",
                "x-delivery-status",
                "delivery-status",
                "final-recipient",
                "diagnostic-code"
            ]

            for header in headers:
                name = header.get("name", "").lower()
                value = header.get("value", "").lower()

                # Most common real-world indicators
                if name in bounce_indicators:
                    return {"bounced": True, "reason": value}

                if any(keyword in value for keyword in [
                    "delivery failed",
                    "undeliverable",
                    "bounce",
                    "failure notice"
                ]):
                    return {"bounced": True, "reason": value}

            return None

        except Exception:
            # Gmail API issues → assume no bounce (don’t break pipeline)
            return None
