from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError

from typing import Optional, Tuple
import os

from src.config import (
    SCOPES, AUTH_MODE, OAUTH_CREDENTIALS_PATH, OAUTH_TOKEN_PATH,
    SERVICE_ACCOUNT_PATH
)


class GoogleAuthenticator:
    """
    Handles authentication for Google APIs using either OAuth2 or Service Account.
    """

    def __init__(self, mode: str = AUTH_MODE):
        self.mode = mode
        self.creds: Optional[Credentials] = None

    # ---------------------------
    # Main authenticate
    # ---------------------------
    def authenticate(self) -> Credentials:
        """Authenticate and return Google API credentials."""
        if self.mode == "oauth":
            self.creds = self._oauth_authenticate()
        elif self.mode == "service_account":
            self.creds = self._service_account_authenticate()
        else:
            raise ValueError(f"Invalid auth mode: {self.mode}")

        return self.creds

    # ---------------------------
    # OAuth2
    # ---------------------------
    def _oauth_authenticate(self) -> Credentials:
        creds = None

        if OAUTH_TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(
                str(OAUTH_TOKEN_PATH),
                SCOPES
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    # Try to refresh the token
                    creds.refresh(Request())
                    print("✅ Token refreshed successfully")
                except RefreshError as e:
                    # Token has been revoked or is invalid - delete it and re-authenticate
                    print(f"⚠️  Token refresh failed: {e}")
                    print("🔄 Token has been revoked or expired. Starting re-authentication...")

                    # Delete the invalid token file
                    if OAUTH_TOKEN_PATH.exists():
                        try:
                            os.remove(OAUTH_TOKEN_PATH)
                            print(f"🗑️  Removed invalid token file: {OAUTH_TOKEN_PATH}")
                        except Exception as remove_error:
                            print(f"⚠️  Could not remove token file: {remove_error}")

                    # Set creds to None to trigger re-authentication
                    creds = None

            # If creds is None (either never existed, invalid, or refresh failed), re-authenticate
            if not creds:
                if not OAUTH_CREDENTIALS_PATH.exists():
                    raise FileNotFoundError(
                        f"OAuth credentials file not found: {OAUTH_CREDENTIALS_PATH}\n"
                        "Download OAuth client credentials from Google Cloud Console."
                    )

                print("🔐 Starting OAuth authentication flow...")
                print("📱 Your browser will open for authentication.")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(OAUTH_CREDENTIALS_PATH),
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("✅ Authentication successful!")

            # Save the credentials
            OAUTH_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OAUTH_TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
            print(f"💾 Credentials saved to: {OAUTH_TOKEN_PATH}")

        return creds

    # ---------------------------
    # Service Account
    # ---------------------------
    def _service_account_authenticate(self) -> Credentials:
        if not SERVICE_ACCOUNT_PATH.exists():
            raise FileNotFoundError(
                f"Service account file not found: {SERVICE_ACCOUNT_PATH}\n"
                "Download the service account JSON key."
            )

        return service_account.Credentials.from_service_account_file(
            str(SERVICE_ACCOUNT_PATH),
            scopes=SCOPES
        )

    # ---------------------------
    # Gmail API
    # ---------------------------
    def get_gmail_service(self):
        if not self.creds:
            self.authenticate()

        if self.mode == "service_account":
            raise ValueError(
                "Service Accounts cannot send Gmail emails. Use OAuth2 mode."
            )

        return build("gmail", "v1", credentials=self.creds)

    # ---------------------------
    # Sheets API
    # ---------------------------
    def get_sheets_service(self):
        if not self.creds:
            self.authenticate()

        return build("sheets", "v4", credentials=self.creds)

    # ---------------------------
    # Static helper for both services
    # ---------------------------
    @staticmethod
    def get_authenticated_services() -> Tuple[Optional[object], object]:
        """
        Return (gmail_service, sheets_service).
        Gmail is only returned for OAuth mode.
        """
        auth = GoogleAuthenticator()
        auth.authenticate()

        gmail_service = auth.get_gmail_service() if AUTH_MODE == "oauth" else None
        sheets_service = auth.get_sheets_service()

        return gmail_service, sheets_service


def get_authenticated_services():
    """
    Public helper that your CLI imports.
    Simply calls the staticmethod above.
    """
    return GoogleAuthenticator.get_authenticated_services()