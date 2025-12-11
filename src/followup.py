from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.sheets import SheetsClient
from src.mailer import GmailMailer
from src.attachments import AttachmentSelector
from src.utils import is_followup_due, validate_email


console = Console()


class FollowupEngine:
    """Engine for processing automated follow-ups across EN/FR sheets."""

    def __init__(
        self,
        sheets_client: SheetsClient,
        mailer: GmailMailer,
        attachment_selector: AttachmentSelector
    ):
        self.sheets = sheets_client
        self.mailer = mailer
        self.attachments = attachment_selector

    # ---------------------------------------------------------
    # MAIN ENGINE
    # ---------------------------------------------------------
    def process_followups(self, language: str = "both", dry_run: bool = False) -> Dict[str, Any]:
        """
        Process all due follow-ups for specified language(s).

        Args:
            language: 'en', 'fr', or 'both'
            dry_run: If True, previews emails without sending

        Returns:
            Stats dict with: {sent, skipped, failed, errors}
        """
        if language not in {"en", "fr", "both"}:
            raise ValueError("language must be 'en', 'fr', or 'both'")

        languages = ["en", "fr"] if language == "both" else [language]

        stats = {
            "sent": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }

        for lang in languages:
            console.print(f"\n[bold]Processing {lang.upper()} follow-ups...[/bold]")

            applications = self.sheets.get_applications_for_followup(lang)

            # Filter due
            due_apps = [app for app in applications if is_followup_due(app["next_followup_date"])]

            if not due_apps:
                console.print(f"[green]No follow-ups due for {lang.upper()}[/green]")
                continue

            console.print(f"[cyan]Found {len(due_apps)} applications needing follow-up[/cyan]")

            # Process pipeline
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:

                task = progress.add_task("Processing follow-ups...", total=len(due_apps))

                for app in due_apps:
                    progress.update(task, description=f"{app['email']}")

                    result = self._process_single_followup(app, lang, dry_run)

                    if result["status"] == "sent":
                        stats["sent"] += 1
                    elif result["status"] == "skipped":
                        stats["skipped"] += 1
                    else:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "email": app["email"],
                            "error": result.get("error", "Unknown error")
                        })

                    progress.advance(task)

        # Summary
        console.print("\n[bold]Follow-up Summary:[/bold]")
        console.print(f"  ✓ Sent: {stats['sent']}")
        console.print(f"  ⊘ Skipped: {stats['skipped']}")
        console.print(f"  ✗ Failed: {stats['failed']}")

        if stats["errors"]:
            console.print("\n[red]Errors:[/red]")
            for err in stats["errors"]:
                console.print(f"  - {err['email']}: {err['error']}")

        return stats

    # ---------------------------------------------------------
    # SINGLE FOLLOW-UP HANDLER
    # ---------------------------------------------------------
    def _process_single_followup(
        self,
        app: Dict[str, Any],
        language: str,
        dry_run: bool
    ) -> Dict[str, str]:
        """Process follow-up for a single application."""

        app_id = app["id"]
        email = app["email"]

        # ------ VALIDATIONS ------
        if not email or not validate_email(email):
            self.sheets.log_activity(app_id, email, "followup_skipped", "failed", "Invalid email address")
            return {"status": "skipped", "error": "Invalid email"}

        if not app.get("body"):
            self.sheets.log_activity(app_id, email, "followup_skipped", "failed", "Missing email body")
            return {"status": "skipped", "error": "Missing body"}

        if not app.get("cv"):
            self.sheets.log_activity(app_id, email, "followup_skipped", "failed", "Missing CV filename")
            return {"status": "skipped", "error": "Missing CV"}

        subject = app.get("position", "").strip()
        if not subject:
            subject = "Follow-up"

        # Check attachment
        attachment_path = self.attachments.get_attachment_path(language, app["cv"])
        if not attachment_path:
            self.sheets.log_activity(
                app_id, email, "followup_skipped", "failed",
                f"Attachment not found: {app['cv']}"
            )
            return {"status": "skipped", "error": f"Attachment not found: {app['cv']}"}

        # ------ DRY RUN ------
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would send follow-up to {email}[/yellow]")
            return {"status": "sent"}

        # ------ SEND EMAIL ------
        try:
            result = self.mailer.send_with_delay(
                to_email=email,
                subject=subject,
                body=app["body"],
                attachment_path=attachment_path
            )

            new_followup_count = app["followups"] + 1
            self.sheets.update_application_followup(app_id, language, new_followup_count)

            self.sheets.log_activity(
                app_id, email, "followup_sent", "success",
                f"Follow-up #{new_followup_count} sent"
            )

            # Bounce check
            msg_id = result.get("id")
            if msg_id:
                bounce_info = self.mailer.check_bounces(msg_id)
                if bounce_info:
                    self.sheets.update_application_status(app_id, language, "Bounced")
                    self.sheets.log_activity(
                        app_id, email, "bounce_detected", "bounced",
                        bounce_info.get("reason", "Unknown")
                    )

            console.print(f"[green]✓ Sent follow-up to {email}[/green]")
            return {"status": "sent"}

        except Exception as e:
            error_msg = str(e)
            self.sheets.log_activity(app_id, email, "followup_failed", "failed", error_msg)
            console.print(f"[red]✗ Failed to send to {email}: {error_msg}[/red]")
            return {"status": "failed", "error": error_msg}
