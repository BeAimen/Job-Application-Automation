import base64
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Optional
import time
import random
import socket

import backoff
from googleapiclient.discovery import Resource
from urllib.parse import quote

from src.config import GMAIL_USER_EMAIL, DEFAULT_DELAY_BETWEEN_EMAILS, MAX_RETRIES


class GmailMailer:
    """Gmail API wrapper for sending emails with proper authentication headers."""

    def __init__(self, service: Resource):
        self.service = service
        self.user_email = GMAIL_USER_EMAIL
        # Extract display name from environment or use default
        self.display_name = "Aimen Berkane"  # ✅ Professional sender name
        self.hostname = socket.getfqdn()  # Get machine hostname for Message-ID

    # ---------------------------------------------------------
    # EMAIL SENDING (WITH AUTHENTICATION HEADERS)
    # ---------------------------------------------------------
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=MAX_RETRIES,
        giveup=lambda e: isinstance(e, ValueError)
    )
    def send_email(
            self,
            to_email: str,
            subject: str,
            body: str,
            attachment_path: Optional[Path] = None
    ) -> dict:
        """
        Send an email using Gmail API with proper authentication headers.

        This adds SPF/DKIM-friendly headers to improve deliverability
        and reduce spam flags.
        """

        # ----------- VALIDATION -----------
        if not to_email:
            raise ValueError("Recipient email is required.")
        if not subject.strip():
            raise ValueError("Email subject cannot be empty.")
        if not body.strip():
            raise ValueError("Email body cannot be empty.")

        # ----------- CREATE MESSAGE WITH PROPER HEADERS -----------
        message = MIMEMultipart()

        # ✅ CRITICAL: Proper From header with display name
        message["From"] = formataddr((self.display_name, self.user_email))

        # ✅ To header
        message["To"] = to_email

        # ✅ Subject
        message["Subject"] = subject

        # ✅ AUTHENTICATION HEADERS
        # These help email providers verify the message is legitimate
        message["Reply-To"] = formataddr((self.display_name, self.user_email))
        message["Return-Path"] = self.user_email

        # ✅ Date header (RFC 2822 format)
        message["Date"] = formatdate(localtime=True)

        # ✅ Message-ID (helps threading and prevents duplicates)
        message["Message-ID"] = make_msgid(domain=self.hostname)

        # ✅ MIME Version
        message["MIME-Version"] = "1.0"

        # ✅ X-Mailer (identifies sender application)
        message["X-Mailer"] = "JobFlow Application Manager v1.0"

        # ✅ X-Priority (normal priority - don't look spammy)
        message["X-Priority"] = "3"  # 3 = Normal (1=High, 5=Low)
        message["Priority"] = "normal"
        message["Importance"] = "normal"

        # ✅ Content headers for better parsing
        message["Content-Language"] = "en-US"

        # ----------- EMAIL BODY -----------
        # Use UTF-8 encoding for international characters
        text_part = MIMEText(body, "plain", "utf-8")
        text_part["Content-Transfer-Encoding"] = "quoted-printable"
        message.attach(text_part)

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

            # ✅ Proper filename encoding (UTF-8 + RFC 2231)
            filename = attachment_path.name
            encoded_filename = Header(filename, "utf-8").encode()
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=encoded_filename
            )
            part.set_param(
                "filename*",
                f"utf-8''{quote(filename)}",
                header="Content-Disposition"
            )
            message.attach(part)

        # ----------- ENCODE MESSAGE FOR GMAIL API -----------
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # ----------- SEND REQUEST -----------
        try:
            result = self.service.users().messages().send(
                userId="me",
                body={"raw": raw_message}
            ).execute()

            print(f"✅ Email sent successfully to {to_email} (Message ID: {result.get('id')})")
            return result

        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            raise

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

        Recommended: 2-5 seconds between emails
        """
        # Add random jitter (0-1 second) to avoid burst detection
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
            # Gmail API issues → assume no bounce (don't break pipeline)
            return None