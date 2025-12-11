from typing import List, Dict, Optional, Any
from googleapiclient.discovery import Resource

from src.config import SPREADSHEET_ID, SHEET_EN, SHEET_FR, SHEET_ACTIVITY
from src.utils import (
    generate_id, get_current_timestamp, calculate_next_followup,
    get_default_company, get_default_position
)


# Column order (MUST match sheet structure)
APPLICATION_COLUMNS = [
    'ID', 'Company', 'Email', 'Position', 'Status', 'Sent Date',
    'Followups', 'Next Followup Date', 'Phone Number', 'Website',
    'Body', 'CV', 'Notes'
]

ACTIVITY_LOG_COLUMNS = [
    'Timestamp', 'ID', 'Email', 'Action', 'Result', 'Details'
]


class SheetsClient:
    """Client for interacting with Google Sheets API."""

    def __init__(self, service: Resource):
        self.service = service
        self.spreadsheet_id = SPREADSHEET_ID

    # ---------------------------------------------------------
    # SHEET SETUP
    # ---------------------------------------------------------
    def _get_sheet_name(self, language: str) -> str:
        """Return sheet name for given language."""
        return SHEET_EN if language == 'en' else SHEET_FR

    def initialize_sheets(self):
        """Initialize sheet headers if they don't exist."""
        self._ensure_headers(SHEET_EN, APPLICATION_COLUMNS)
        self._ensure_headers(SHEET_FR, APPLICATION_COLUMNS)
        self._ensure_headers(SHEET_ACTIVITY, ACTIVITY_LOG_COLUMNS)

    def _ensure_headers(self, sheet_name: str, headers: List[str]):
        """Ensure sheet contains the correct header row."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1:Z1"
            ).execute()

            existing = result.get("values", [[]])
            existing_headers = existing[0] if existing else []

            if existing_headers != headers:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption="RAW",
                    body={"values": [headers]}
                ).execute()

        except Exception as e:
            print(f"[ERROR] Failed to ensure headers for {sheet_name}: {e}")

    # ---------------------------------------------------------
    # APPLICATION CREATION
    # ---------------------------------------------------------
    def add_application(
        self,
        email: str,
        language: str,
        company: Optional[str] = None,
        position: Optional[str] = None,
        body: Optional[str] = None,
        cv_filename: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        notes: Optional[str] = None,
        status: str = 'Pending'
    ) -> str:
        """Insert a new application row and return the application ID."""

        sheet_name = self._get_sheet_name(language)
        app_id = generate_id()

        company = company.strip() if company else get_default_company(language)
        position = position.strip() if position else get_default_position(language)

        row = [
            app_id,
            company,
            email,
            position,
            status,
            "",            # Sent Date
            0,             # Followups
            "",            # Next Followup Date
            phone or "",
            website or "",
            body or "",
            cv_filename or "",
            notes or ""
        ]

        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!A:M",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]}
        ).execute()

        return app_id

    # ---------------------------------------------------------
    # UPDATE AFTER SEND
    # ---------------------------------------------------------
    def update_application_sent(self, app_id: str, language: str, body: str, cv_filename: str):
        """Update sheet after email is successfully sent."""
        sheet_name = self._get_sheet_name(language)

        row_index = self._find_row_by_id(sheet_name, app_id)
        if not row_index:
            raise ValueError(f"Application ID {app_id} not found")

        sent_date = get_current_timestamp()
        next_followup = calculate_next_followup(sent_date)

        updates = [
            {"range": f"{sheet_name}!E{row_index}", "values": [["Sent"]]},
            {"range": f"{sheet_name}!F{row_index}", "values": [[sent_date]]},
            {"range": f"{sheet_name}!H{row_index}", "values": [[next_followup]]},
            {"range": f"{sheet_name}!K{row_index}", "values": [[body]]},
            {"range": f"{sheet_name}!L{row_index}", "values": [[cv_filename]]},
        ]

        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"data": updates, "valueInputOption": "RAW"}
        ).execute()

    # ---------------------------------------------------------
    # UPDATE FOLLOW-UP
    # ---------------------------------------------------------
    def update_application_followup(self, app_id: str, language: str, followup_count: int):
        """Update followup count and schedule next followup."""
        sheet_name = self._get_sheet_name(language)

        row_index = self._find_row_by_id(sheet_name, app_id)
        if not row_index:
            raise ValueError(f"Application ID {app_id} not found")

        last_followup_date = self._get_cell_value(sheet_name, row_index, 8)
        next_followup = calculate_next_followup(last_followup_date)

        updates = [
            {"range": f"{sheet_name}!G{row_index}", "values": [[followup_count]]},
            {"range": f"{sheet_name}!H{row_index}", "values": [[next_followup]]},
            {"range": f"{sheet_name}!E{row_index}", "values": [["Follow-up Sent"]]},
        ]

        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"data": updates, "valueInputOption": "RAW"}
        ).execute()

    # ---------------------------------------------------------
    # STATUS UPDATE
    # ---------------------------------------------------------
    def update_application_status(self, app_id: str, language: str, status: str):
        """Set application status to a new value."""
        sheet_name = self._get_sheet_name(language)

        row_index = self._find_row_by_id(sheet_name, app_id)
        if not row_index:
            raise ValueError(f"Application ID {app_id} not found")

        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!E{row_index}",
            valueInputOption="RAW",
            body={"values": [[status]]}
        ).execute()

    # ---------------------------------------------------------
    # RETRIEVE FOLLOWUP-DUE APPLICATIONS
    # ---------------------------------------------------------
    def get_applications_for_followup(self, language: str) -> List[Dict[str, Any]]:
        """Return applications that require follow-up."""
        sheet_name = self._get_sheet_name(language)

        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!A2:M"
        ).execute()

        rows = result.get("values", [])
        applications = []

        for row in rows:
            if len(row) < 8:
                continue

            status = row[4] if len(row) > 4 else ""

            if status in {"Bounced", "Failed", "Frozen"}:
                continue

            next_followup = row[7] if len(row) > 7 else ""

            if not next_followup:
                continue

            applications.append({
                "id": row[0],
                "company": row[1] if len(row) > 1 else "",
                "email": row[2] if len(row) > 2 else "",
                "position": row[3] if len(row) > 3 else "",
                "status": status,
                "sent_date": row[5] if len(row) > 5 else "",
                "followups": int(row[6]) if len(row) > 6 and row[6] else 0,
                "next_followup_date": next_followup,
                "phone": row[8] if len(row) > 8 else "",
                "website": row[9] if len(row) > 9 else "",
                "body": row[10] if len(row) > 10 else "",
                "cv": row[11] if len(row) > 11 else "",
                "notes": row[12] if len(row) > 12 else "",
            })

        return applications

    # ---------------------------------------------------------
    # ACTIVITY LOG
    # ---------------------------------------------------------
    def log_activity(self, app_id: str, email: str, action: str, result: str, details: str = ""):
        """Append an activity log entry."""
        timestamp = get_current_timestamp()

        row = [timestamp, app_id, email, action, result, details]

        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{SHEET_ACTIVITY}!A:F",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]}
        ).execute()

    # ---------------------------------------------------------
    # LOOKUP HELPERS
    # ---------------------------------------------------------
    def get_application_by_id(self, app_id: str, language: str) -> Optional[Dict[str, Any]]:
        """Return full application details for a given ID."""
        sheet_name = self._get_sheet_name(language)

        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!A2:M"
        ).execute()

        for row in result.get("values", []):
            if row and row[0] == app_id:
                return {
                    "id": row[0],
                    "company": row[1] if len(row) > 1 else "",
                    "email": row[2] if len(row) > 2 else "",
                    "position": row[3] if len(row) > 3 else "",
                    "status": row[4] if len(row) > 4 else "",
                    "sent_date": row[5] if len(row) > 5 else "",
                    "followups": row[6] if len(row) > 6 else "",
                    "next_followup_date": row[7] if len(row) > 7 else "",
                    "phone": row[8] if len(row) > 8 else "",
                    "website": row[9] if len(row) > 9 else "",
                    "body": row[10] if len(row) > 10 else "",
                    "cv": row[11] if len(row) > 11 else "",
                    "notes": row[12] if len(row) > 12 else "",
                }

        return None

    def _find_row_by_id(self, sheet_name: str, app_id: str) -> Optional[int]:
        """Find row index (1-based) for a given ID."""
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!A:A"
        ).execute()

        for i, row in enumerate(result.get("values", []), start=1):
            if row and row[0] == app_id:
                return i

        return None

    def _get_cell_value(self, sheet_name: str, row: int, col: int) -> str:
        """Return content of a given cell (1-indexed)."""
        col_letter = chr(64 + col)  # 1 = A, 2 = B, ...

        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!{col_letter}{row}"
        ).execute()

        values = result.get("values", [])
        return values[0][0] if values and values[0] else ""
