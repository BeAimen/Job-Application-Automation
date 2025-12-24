import pytest
from unittest.mock import Mock, MagicMock, patch

from src.sheets import SheetsClient, APPLICATION_COLUMNS
from src.config import DEFAULTS


@pytest.fixture
def mock_service():
    """Create a fully chained mock Google Sheets service."""
    service = Mock()

    # Mock spreadsheets()
    mock_spreadsheets = Mock()
    service.spreadsheets.return_value = mock_spreadsheets

    # Mock spreadsheets().values()
    mock_values = Mock()
    mock_spreadsheets.values.return_value = mock_values

    # Mock append().execute()
    mock_values.append.return_value.execute.return_value = {}

    return service


@pytest.fixture
def sheets_client(mock_service):
    """Create SheetsClient with mock service and patched SPREADSHEET_ID."""
    with patch('src.sheets.SPREADSHEET_ID', 'test_sheet_id'):
        return SheetsClient(mock_service)


# ---------------------------------------------------------
# TEST: add_application (normal case)
# ---------------------------------------------------------
def test_add_application(sheets_client, mock_service):
    """Test adding a full application row."""

    app_id = sheets_client.add_application(
        email="test@example.com",
        language="en",
        company="Test Corp",
        position="Engineer"
    )

    # UUID generated
    assert app_id is not None
    assert len(app_id) == 36

    # Verify append was called
    mock_service.spreadsheets().values().append.assert_called_once()


# ---------------------------------------------------------
# TEST: add_application (defaults)
# ---------------------------------------------------------
def test_add_application_with_defaults(sheets_client, mock_service):
    """Test applying default company + position when missing."""

    app_id = sheets_client.add_application(
        email="test@example.com",
        language="en"
    )

    assert app_id is not None

    # Retrieve the arguments sent to append(...)
    call_args = mock_service.spreadsheets().values().append.call_args
    values = call_args.kwargs['body']['values'][0]

    # Column positions:
    # 0: ID
    # 1: Company
    # 3: Position

    expected_company = DEFAULTS["en"]["company_unknown"]
    expected_position = DEFAULTS["en"]["position"]

    assert values[1] == expected_company
    assert values[3] == expected_position


# ---------------------------------------------------------
# TEST: column order
# ---------------------------------------------------------
def test_column_order():
    """Ensure column structure is correct."""
    expected = [
        'ID', 'Company', 'Email', 'Position', 'Status', 'Sent Date',
        'Followups', 'Next Followup Date', 'Phone Number', 'Website',
        'Body', 'CV', 'Notes', 'Type', 'Salary', 'Place', 'Reference Link'
    ]
    assert APPLICATION_COLUMNS == expected
