from typing import List, Dict, Optional, Any
from googleapiclient.discovery import Resource

from src.config import SPREADSHEET_ID, SHEET_EN, SHEET_FR, SHEET_ACTIVITY, SHEET_COMPANIES
from src.utils import (
    generate_id, get_current_timestamp, calculate_next_followup,
    get_default_company, get_default_position
)

# Add to the top of src/sheets.py after imports:
import time as time_module
from src.monitoring import system_monitor


APPLICATION_COLUMNS = [
    'ID', 'Company', 'Email', 'Position', 'Status', 'Sent Date',
    'Followups', 'Next Followup Date', 'Phone Number', 'Website',
    'Body', 'CV', 'Notes', 'Type', 'Salary', 'Place', 'Reference'
]

COMPANY_COLUMNS = [
    'ID', 'Company Name', 'Type', 'Email', 'Phone', 'Website',
    'Location', 'Reference', 'Salary Range', 'Notes',
    'Added Date', 'Last Updated'
]

ACTIVITY_LOG_COLUMNS = [
    'Timestamp', 'ID', 'Email', 'Action', 'Result', 'Details'
]


class SheetsClient:
    """Client for interacting with Google Sheets API."""

    def __init__(self, service: Resource):
        self.service = service
        self.spreadsheet_id = SPREADSHEET_ID

    # Add these wrapper methods to track API calls:
    def _execute_sheets_api(self, operation_name: str, api_call):
        """Execute a Sheets API call with monitoring."""
        start_time = time_module.time()

        try:
            result = api_call()
            duration_ms = (time_module.time() - start_time) * 1000

            # Log successful API call
            system_monitor.log_api_call('sheets', operation_name, True, duration_ms)

            return result

        except Exception as e:
            duration_ms = (time_module.time() - start_time) * 1000

            # Log failed API call
            system_monitor.log_api_call('sheets', operation_name, False, duration_ms)

            # Log error event
            system_monitor.log_event(
                'sheets_api_error',
                'error',
                f'Sheets API error in {operation_name}',
                {'error': str(e), 'duration_ms': round(duration_ms, 2)}
            )

            raise

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
        self._ensure_headers(SHEET_COMPANIES, COMPANY_COLUMNS)  # NEW

    def _ensure_headers(self, sheet_name: str, headers: List[str]):
        """Ensure sheet contains the correct header row."""
        try:
            result = self._execute_sheets_api(
                'get_headers',
                lambda: self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{sheet_name}!A1:Z1"
                ).execute()
            )

            existing = result.get("values", [[]])
            existing_headers = existing[0] if existing else []

            if existing_headers != headers:
                self._execute_sheets_api(
                    'update_headers',
                    lambda: self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"{sheet_name}!A1",
                        valueInputOption="RAW",
                        body={"values": [headers]}
                    ).execute()
                )

        except Exception as e:
            print(f"[ERROR] Failed to ensure headers for {sheet_name}: {e}")

    # ---------------------------------------------------------
    # APPLICATION CREATION (UPDATED with new fields)
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
        status: str = 'Pending',
        company_type: Optional[str] = None,  # NEW
        salary: Optional[str] = None,  # NEW
        place: Optional[str] = None,  # NEW
        reference: Optional[str] = None  # NEW
    ) -> str:
        """Insert a new application row and return the application ID."""

        system_monitor.log_event(
            'application_created',
            'info',
            f'Creating application for {email}',
            {'language': language, 'company': company}
        )

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
            notes or "",
            company_type or "",  # NEW
            salary or "",  # NEW
            place or "",  # NEW
            reference or ""  # NEW
        ]

        # Use monitored API call
        self._execute_sheets_api(
            'append_row',
            lambda: self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:Q",  # Updated range to include new columns
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]}
            ).execute()
        )

        system_monitor.log_event(
            'application_added',
            'info',
            f'Application added successfully',
            {'app_id': app_id, 'email': email, 'language': language}
        )

        return app_id

    # ---------------------------------------------------------
    # UPDATE AFTER SEND (UPDATED)
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

        self._execute_sheets_api(
            'batch_update_application_sent',
            lambda: self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"data": updates, "valueInputOption": "RAW"}
            ).execute()
        )

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

        self._execute_sheets_api(
            'batch_update_application_followup',
            lambda: self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"data": updates, "valueInputOption": "RAW"}
            ).execute()
        )

    # ---------------------------------------------------------
    # STATUS UPDATE
    # ---------------------------------------------------------
    def update_application_status(self, app_id: str, language: str, status: str):
        """Set application status to a new value."""
        sheet_name = self._get_sheet_name(language)

        row_index = self._find_row_by_id(sheet_name, app_id)
        if not row_index:
            raise ValueError(f"Application ID {app_id} not found")

        self._execute_sheets_api(
            'update_application_status',
            lambda: self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!E{row_index}",
                valueInputOption="RAW",
                body={"values": [[status]]}
            ).execute()
        )

    # ---------------------------------------------------------
    # RETRIEVE FOLLOWUP-DUE APPLICATIONS (UPDATED)
    # ---------------------------------------------------------
    def get_applications_for_followup(self, language: str) -> List[Dict[str, Any]]:
        """Return applications that require follow-up."""
        sheet_name = self._get_sheet_name(language)

        result = self._execute_sheets_api(
            'get_applications_for_followup',
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A2:Q"  # Updated range
            ).execute()
        )

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
                "language": language,
                "status": status,
                "sent_date": row[5] if len(row) > 5 else "",
                "followups": int(row[6]) if len(row) > 6 and row[6] else 0,
                "next_followup_date": next_followup,
                "phone": row[8] if len(row) > 8 else "",
                "website": row[9] if len(row) > 9 else "",
                "body": row[10] if len(row) > 10 else "",
                "cv": row[11] if len(row) > 11 else "",
                "notes": row[12] if len(row) > 12 else "",
                "type": row[13] if len(row) > 13 else "",  # NEW
                "salary": row[14] if len(row) > 14 else "",  # NEW
                "place": row[15] if len(row) > 15 else "",  # NEW
                "reference": row[16] if len(row) > 16 else "",  # NEW
            })

        return applications

    # ---------------------------------------------------------
    # ACTIVITY LOG
    # ---------------------------------------------------------
    def log_activity(self, app_id: str, email: str, action: str, result: str, details: str = ""):
        """Append an activity log entry."""
        timestamp = get_current_timestamp()

        row = [timestamp, app_id, email, action, result, details]

        self._execute_sheets_api(
            'append_activity_log',
            lambda: self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{SHEET_ACTIVITY}!A:F",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]}
            ).execute()
        )

    # ---------------------------------------------------------
    # LOOKUP HELPERS (UPDATED)
    # ---------------------------------------------------------
    def get_application_by_id(self, app_id: str, language: str) -> Optional[Dict[str, Any]]:
        """Return full application details for a given ID."""
        sheet_name = self._get_sheet_name(language)

        result = self._execute_sheets_api(
            'get_application_by_id',
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A2:Q"  # Updated range
            ).execute()
        )

        for row in result.get("values", []):
            if row and row[0] == app_id:
                return {
                    "id": row[0],
                    "company": row[1] if len(row) > 1 else "",
                    "email": row[2] if len(row) > 2 else "",
                    "position": row[3] if len(row) > 3 else "",
                    "language": language,
                    "status": row[4] if len(row) > 4 else "",
                    "sent_date": row[5] if len(row) > 5 else "",
                    "followups": row[6] if len(row) > 6 else "",
                    "next_followup_date": row[7] if len(row) > 7 else "",
                    "phone": row[8] if len(row) > 8 else "",
                    "website": row[9] if len(row) > 9 else "",
                    "body": row[10] if len(row) > 10 else "",
                    "cv": row[11] if len(row) > 11 else "",
                    "notes": row[12] if len(row) > 12 else "",
                    "type": row[13] if len(row) > 13 else "",  # NEW
                    "salary": row[14] if len(row) > 14 else "",  # NEW
                    "place": row[15] if len(row) > 15 else "",  # NEW
                    "reference": row[16] if len(row) > 16 else "",  # NEW
                }

        return None

    def _find_row_by_id(self, sheet_name: str, app_id: str) -> Optional[int]:
        """Find row index (1-based) for a given ID."""
        result = self._execute_sheets_api(
            'find_row_by_id',
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A"
            ).execute()
        )

        for i, row in enumerate(result.get("values", []), start=1):
            if row and row[0] == app_id:
                return i

        return None

    def _get_cell_value(self, sheet_name: str, row: int, col: int) -> str:
        """Return content of a given cell (1-indexed)."""
        col_letter = chr(64 + col)  # 1 = A, 2 = B, ...

        result = self._execute_sheets_api(
            'get_cell_value',
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{col_letter}{row}"
            ).execute()
        )

        values = result.get("values", [])
        return values[0][0] if values and values[0] else ""

    def find_application_by_email(self, email: str, language: str) -> Optional[Dict[str, Any]]:
        """Find an application by recipient email (case-insensitive)."""
        sheet_name = self._get_sheet_name(language)

        result = self._execute_sheets_api(
            'find_application_by_email',
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A2:Q"
            ).execute()
        )

        rows = result.get("values", [])
        for idx, row in enumerate(rows, start=2):
            if len(row) > 2 and row[2] and row[2].lower() == email.lower():
                return {
                    "id": row[0],
                    "row_index": idx
                }
        return None

    def update_application_fields(
        self,
        app_id: str,
        language: str,
        company: Optional[str] = None,
        position: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        notes: Optional[str] = None,
        company_type: Optional[str] = None,
        salary: Optional[str] = None,
        place: Optional[str] = None,
        reference: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """Update application fields without creating a new row."""
        sheet_name = self._get_sheet_name(language)
        row_index = self._find_row_by_id(sheet_name, app_id)
        if not row_index:
            return False

        updates = []
        if company is not None:
            updates.append({"range": f"{sheet_name}!B{row_index}", "values": [[company]]})
        if position is not None:
            updates.append({"range": f"{sheet_name}!D{row_index}", "values": [[position]]})
        if status is not None:
            updates.append({"range": f"{sheet_name}!E{row_index}", "values": [[status]]})
        if phone is not None:
            updates.append({"range": f"{sheet_name}!I{row_index}", "values": [[phone]]})
        if website is not None:
            updates.append({"range": f"{sheet_name}!J{row_index}", "values": [[website]]})
        if notes is not None:
            updates.append({"range": f"{sheet_name}!M{row_index}", "values": [[notes]]})
        if company_type is not None:
            updates.append({"range": f"{sheet_name}!N{row_index}", "values": [[company_type]]})
        if salary is not None:
            updates.append({"range": f"{sheet_name}!O{row_index}", "values": [[salary]]})
        if place is not None:
            updates.append({"range": f"{sheet_name}!P{row_index}", "values": [[place]]})
        if reference is not None:
            updates.append({"range": f"{sheet_name}!Q{row_index}", "values": [[reference]]})

        if updates:
            self._execute_sheets_api(
                'update_application_fields',
                lambda: self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"data": updates, "valueInputOption": "RAW"}
                ).execute()
            )

        return True

    # ==========================================================
    # COMPANIES MANAGEMENT (NEW SECTION)
    # ==========================================================

    def add_company(
        self,
        company_name: str,
        company_type: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        location: Optional[str] = None,
        reference: Optional[str] = None,
        salary_range: Optional[str] = None,
        notes: Optional[str] = None
    ) -> str:
        """Add a new company to the Companies sheet."""
        company_id = generate_id()
        added_date = get_current_timestamp()

        row = [
            company_id,
            company_name,
            company_type or "",
            email or "",
            phone or "",
            website or "",
            location or "",
            reference or "",
            salary_range or "",
            notes or "",
            added_date,
            added_date  # Last Updated
        ]

        self._execute_sheets_api(
            'add_company',
            lambda: self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{SHEET_COMPANIES}!A:L",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]}
            ).execute()
        )

        return company_id

    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Get all companies from the Companies sheet."""
        try:
            result = self._execute_sheets_api(
                'get_all_companies',
                lambda: self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{SHEET_COMPANIES}!A2:L"
                ).execute()
            )

            rows = result.get("values", [])
            companies = []

            for row in rows:
                if len(row) < 2 or not row[0] or not row[1]:
                    continue

                companies.append({
                    "id": row[0] if len(row) > 0 else "",
                    "name": row[1] if len(row) > 1 else "",
                    "type": row[2] if len(row) > 2 else "",
                    "email": row[3] if len(row) > 3 else "",
                    "phone": row[4] if len(row) > 4 else "",
                    "website": row[5] if len(row) > 5 else "",
                    "location": row[6] if len(row) > 6 else "",
                    "reference": row[7] if len(row) > 7 else "",
                    "salary_range": row[8] if len(row) > 8 else "",
                    "notes": row[9] if len(row) > 9 else "",
                    "added_date": row[10] if len(row) > 10 else "",
                    "last_updated": row[11] if len(row) > 11 else ""
                })

            return companies
        except Exception as e:
            print(f"[ERROR] Failed to get companies: {e}")
            return []

    def get_company_by_name(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Find a company by name (case-insensitive)."""
        companies = self.get_all_companies()
        for company in companies:
            if company["name"].lower() == company_name.lower():
                return company
        return None

    def get_company_by_id(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific company by ID."""
        companies = self.get_all_companies()
        for company in companies:
            if company["id"] == company_id:
                return company
        return None

    def update_company(
        self,
        company_id: str,
        company_name: Optional[str] = None,
        company_type: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        location: Optional[str] = None,
        reference: Optional[str] = None,
        salary_range: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Update a company's information."""
        row_index = self._find_row_by_id(SHEET_COMPANIES, company_id)
        if not row_index:
            return False

        last_updated = get_current_timestamp()

        # Get current values
        current = self.get_company_by_id(company_id)
        if not current:
            return False

        # Prepare updates
        updates = []
        if company_name is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!B{row_index}", "values": [[company_name]]})
        if company_type is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!C{row_index}", "values": [[company_type]]})
        if email is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!D{row_index}", "values": [[email]]})
        if phone is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!E{row_index}", "values": [[phone]]})
        if website is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!F{row_index}", "values": [[website]]})
        if location is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!G{row_index}", "values": [[location]]})
        if reference is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!H{row_index}", "values": [[reference]]})
        if salary_range is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!I{row_index}", "values": [[salary_range]]})
        if notes is not None:
            updates.append({"range": f"{SHEET_COMPANIES}!J{row_index}", "values": [[notes]]})

        # Always update last_updated
        updates.append({"range": f"{SHEET_COMPANIES}!L{row_index}", "values": [[last_updated]]})

        if updates:
            self._execute_sheets_api(
                'update_company',
                lambda: self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"data": updates, "valueInputOption": "RAW"}
                ).execute()
            )

        return True

    def upsert_company_from_application(
        self,
        company_name: str,
        emails: List[str],
        company_type: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        location: Optional[str] = None,
        reference: Optional[str] = None,
        salary_range: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[str]:
        """Create or update a company using data provided from an application."""
        if not company_name:
            return None

        normalized_emails = [e.strip() for e in emails if e.strip()]
        email_string = ", ".join(dict.fromkeys([e for e in normalized_emails]))

        existing = self.get_company_by_name(company_name)
        if existing:
            merged_emails = self._merge_emails(existing.get("email", ""), normalized_emails)
            self.update_company(
                company_id=existing["id"],
                company_name=company_name,
                company_type=company_type or existing.get("type", ""),
                email=merged_emails,
                phone=phone or existing.get("phone", ""),
                website=website or existing.get("website", ""),
                location=location or existing.get("location", ""),
                reference=reference or existing.get("reference", ""),
                salary_range=salary_range or existing.get("salary_range", ""),
                notes=notes or existing.get("notes", "")
            )
            return existing["id"]

        return self.add_company(
            company_name=company_name,
            company_type=company_type,
            email=email_string,
            phone=phone,
            website=website,
            location=location,
            reference=reference,
            salary_range=salary_range,
            notes=notes
        )

    @staticmethod
    def _merge_emails(existing_emails: str, new_emails: List[str]) -> str:
        """Combine existing comma-separated emails with new ones, removing duplicates."""
        existing_list = [e.strip() for e in existing_emails.split(",") if e.strip()]
        merged = list(dict.fromkeys(existing_list + new_emails))
        return ", ".join(merged)

    def delete_company(self, company_id: str) -> bool:
        row_index = self._find_row_by_id(SHEET_COMPANIES, company_id)
        if not row_index:
            return False

        # Get sheetId dynamically
        spreadsheet = self._execute_sheets_api(
            'get_spreadsheet',
            lambda: self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
        )

        sheet_id = None
        for sheet in spreadsheet["sheets"]:
            if sheet["properties"]["title"] == SHEET_COMPANIES:
                sheet_id = sheet["properties"]["sheetId"]
                break

        if sheet_id is None:
            return False

        self._execute_sheets_api(
            'delete_company_row',
            lambda: self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    "requests": [{
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": row_index - 1,
                                "endIndex": row_index
                            }
                        }
                    }]
                }
            ).execute()
        )

        return True
