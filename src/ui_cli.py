import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from src.auth import get_authenticated_services
from src.sheets import SheetsClient
from src.mailer import GmailMailer
from src.attachments import AttachmentSelector
from src.followup import FollowupEngine
from src.utils import (
    validate_email, get_default_body, get_default_position,
    substitute_placeholders
)


app = typer.Typer(help="Job Application Automation CLI")
console = Console()


# ---------------------------------------------------------
# CLIENT INITIALIZATION
# ---------------------------------------------------------
def get_clients():
    """Authenticate and initialize Google Sheets + Gmail clients."""
    gmail_service, sheets_service = get_authenticated_services()

    sheets_client = SheetsClient(sheets_service)
    mailer = GmailMailer(gmail_service) if gmail_service else None
    attachment_selector = AttachmentSelector()

    return sheets_client, mailer, attachment_selector


# ---------------------------------------------------------
# INIT COMMAND
# ---------------------------------------------------------
@app.command()
def init():
    """Initialize Google Sheets with correct headers."""
    console.print("[bold]Initializing sheets...[/bold]")

    sheets_client, _, _ = get_clients()
    sheets_client.initialize_sheets()

    console.print("[green]✓ Sheets initialized successfully![/green]")


# ---------------------------------------------------------
# SEND COMMAND
# ---------------------------------------------------------
@app.command()
def send(
    email: List[str] = typer.Option(..., "--email", "-e", help="Recipient email(s)"),
    lang: str = typer.Option("en", "--lang", "-l", help="Language: en, fr, or both"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Company name"),
    position: Optional[str] = typer.Option(None, "--position", "-p", help="Position title"),
    attachment: Optional[str] = typer.Option(None, "--attachment", "-a", help="Attachment filename"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Custom email body"),
    phone: Optional[str] = typer.Option(None, "--phone", help="Phone number"),
    website: Optional[str] = typer.Option(None, "--website", help="Website"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Notes")
):
    """Send job application email(s)."""

    sheets_client, mailer, attachment_selector = get_clients()

    if not mailer:
        console.print("[red]Error: Gmail service not available. Check authentication.[/red]")
        raise typer.Exit(1)

    # Validate emails
    invalid_emails = [e for e in email if not validate_email(e)]
    if invalid_emails:
        console.print(f"[red]Invalid email addresses: {', '.join(invalid_emails)}[/red]")
        raise typer.Exit(1)

    # Validate language
    if lang not in ("en", "fr", "both"):
        console.print("[red]Invalid language. Use: en, fr, both[/red]")
        raise typer.Exit(1)

    languages = ["en", "fr"] if lang == "both" else [lang]

    for language in languages:
        console.print(f"\n[bold]Processing {language.upper()} emails...[/bold]")

        # Defaults
        final_position = position or get_default_position(language)
        final_body_template = body or get_default_body(language)

        # Select attachment
        if attachment:
            attachment_path = attachment_selector.get_attachment_path(language, attachment)
            if not attachment_path:
                console.print(f"[red]Attachment '{attachment}' not found in {language.upper()} folder[/red]")
                continue
        else:
            attachment_path = attachment_selector.select_attachment(language)
            if not attachment_path:
                console.print(f"[yellow]Skipping {language.upper()} - no attachment selected[/yellow]")
                continue

        attachment_filename = attachment_path.name

        # Process each email
        for recipient in email:
            console.print(f"\nProcessing {recipient}...")

            # Add application entry
            app_id = sheets_client.add_application(
                email=recipient,
                language=language,
                company=company,
                position=final_position,
                phone=phone,
                website=website,
                notes=notes,
                status="Pending"
            )

            # Prepare email body
            final_body = substitute_placeholders(
                final_body_template,
                company,
                final_position,
                language
            )

            # Send email
            try:
                result = mailer.send_with_delay(
                    to_email=recipient,
                    subject=final_position,
                    body=final_body,
                    attachment_path=attachment_path
                )

                sheets_client.update_application_sent(app_id, language, final_body, attachment_filename)

                sheets_client.log_activity(
                    app_id, recipient, "email_sent", "success", "Initial application sent"
                )

                console.print(f"[green]✓ Sent to {recipient}[/green]")

            except Exception as e:
                sheets_client.update_application_status(app_id, language, "Failed")
                sheets_client.log_activity(
                    app_id, recipient, "email_failed", "failed", str(e)
                )
                console.print(f"[red]✗ Failed to send to {recipient}: {e}[/red]")

    console.print("\n[bold green]Done![/bold green]")


# ---------------------------------------------------------
# ADD COMMAND
# ---------------------------------------------------------
@app.command()
def add(
    email: str = typer.Option(..., "--email", "-e", help="Email address"),
    lang: str = typer.Option("en", "--lang", "-l", help="Language: en or fr"),
    company: Optional[str] = typer.Option(None, "--company", "-c"),
    position: Optional[str] = typer.Option(None, "--position", "-p"),
    phone: Optional[str] = typer.Option(None, "--phone"),
    website: Optional[str] = typer.Option(None, "--website"),
    notes: Optional[str] = typer.Option(None, "--notes")
):
    """Add an application entry without sending."""

    if not validate_email(email):
        console.print(f"[red]Invalid email address: {email}[/red]")
        raise typer.Exit(1)

    sheets_client, _, _ = get_clients()

    app_id = sheets_client.add_application(
        email=email,
        language=lang,
        company=company,
        position=position,
        phone=phone,
        website=website,
        notes=notes,
        status="Draft"
    )

    sheets_client.log_activity(app_id, email, "application_added", "success", "Added as draft")

    console.print(f"[green]✓ Added application with ID: {app_id}[/green]")


# ---------------------------------------------------------
# FOLLOWUPS COMMAND
# ---------------------------------------------------------
@app.command()
def followups(
    lang: str = typer.Option("both", "--lang", "-l", help="Language: en, fr, or both"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be sent without sending")
):
    """Process all due follow-ups."""

    sheets_client, mailer, attachment_selector = get_clients()

    if not mailer:
        console.print("[red]Error: Gmail service not available. Check authentication.[/red]")
        raise typer.Exit(1)

    if lang not in ("en", "fr", "both"):
        console.print("[red]Invalid language. Use: en, fr, both[/red]")
        raise typer.Exit(1)

    engine = FollowupEngine(sheets_client, mailer, attachment_selector)

    if not dry_run:
        confirm = Confirm.ask("This will send follow-up emails. Continue?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit()

    stats = engine.process_followups(language=lang, dry_run=dry_run)

    console.print("\n[bold]Complete![/bold]")


# ---------------------------------------------------------
# STATUS COMMAND
# ---------------------------------------------------------
@app.command()
def status(
    app_id: str = typer.Argument(..., help="Application ID"),
    lang: str = typer.Option("en", "--lang", "-l", help="Language: en or fr")
):
    """Check status of an application."""

    sheets_client, _, _ = get_clients()

    app = sheets_client.get_application_by_id(app_id, lang)

    if not app:
        console.print(f"[red]Application {app_id} not found in {lang.upper()} sheet[/red]")
        raise typer.Exit(1)

    table = Table(
        title=f"Application {app_id}",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="white")

    for key, value in app.items():
        if key != "body":  # Avoid dumping long body content
            table.add_row(key.title(), str(value))

    console.print(table)
