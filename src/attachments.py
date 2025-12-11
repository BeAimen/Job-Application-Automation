from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from src.config import ATTACHMENT_FOLDER_EN, ATTACHMENT_FOLDER_FR


console = Console()


class AttachmentSelector:
    """Interactive attachment selector for CLI."""

    def __init__(self):
        self.folders = {
            "en": ATTACHMENT_FOLDER_EN,
            "fr": ATTACHMENT_FOLDER_FR,
        }

        # Supported doc formats
        self.extensions = ["*.pdf", "*.docx", "*.doc", "*.rtf"]

    # ---------------------------------------------------------
    # ATTACHMENT RETRIEVAL
    # ---------------------------------------------------------
    def get_attachments(self, language: str) -> List[Path]:
        """Return list of available attachments for a language."""
        folder = self.folders.get(language)

        if not folder or not folder.exists():
            return []

        files = []
        for ext in self.extensions:
            files.extend(folder.glob(ext))

        return sorted(files, key=lambda p: p.name.lower())

    # ---------------------------------------------------------
    # ATTACHMENT SELECTION
    # ---------------------------------------------------------
    def select_attachment(self, language: str, filename: Optional[str] = None) -> Optional[Path]:
        """
        Select an attachment interactively or by filename.

        Args:
            language: 'en' or 'fr'
            filename: if provided, tries to match automatically

        Returns:
            Path to attachment, or None if not found / cancelled.
        """
        attachments = self.get_attachments(language)

        # No attachments
        if not attachments:
            console.print(f"[red]No attachments found in folder: {self.folders.get(language)}[/red]")
            return None

        # -------------------------------
        # 1) Direct Filename Mode
        # -------------------------------
        if filename:
            filename_lower = filename.lower().strip()

            for att in attachments:
                # Match name, name without extension, or case-insensitive
                if (
                    att.name.lower() == filename_lower
                    or att.stem.lower() == filename_lower
                ):
                    return att

            console.print(f"[red]Attachment '{filename}' not found in {language.upper()} folder[/red]")
            return None

        # -------------------------------
        # 2) Interactive Mode
        # -------------------------------
        console.print(f"\n[bold]Available attachments ({language.upper()}):[/bold]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=6)
        table.add_column("Filename")
        table.add_column("Size", justify="right")

        for idx, att in enumerate(attachments, start=1):
            size_kb = att.stat().st_size / 1024
            table.add_row(str(idx), att.name, f"{size_kb:.1f} KB")

        console.print(table)

        # Prompt user
        choice = Prompt.ask(
            "\nSelect attachment number or type filename",
            default="1"
        ).strip()

        # Try numeric selection
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(attachments):
                return attachments[idx]

        # Try filename selection
        choice_lower = choice.lower()

        for att in attachments:
            if att.name.lower() == choice_lower or att.stem.lower() == choice_lower:
                return att

        console.print("[red]Invalid selection[/red]")
        return None

    # ---------------------------------------------------------
    # VALIDATION HELPERS
    # ---------------------------------------------------------
    def validate_attachment(self, language: str, filename: str) -> bool:
        """Return True if filename exists in folder for that language."""
        folder = self.folders.get(language)

        if not folder or not folder.exists():
            return False

        return (folder / filename).exists()

    def get_attachment_path(self, language: str, filename: str) -> Optional[Path]:
        """Return Path to filename if it exists, otherwise None."""
        folder = self.folders.get(language)

        if not folder or not folder.exists():
            return None

        path = folder / filename
        return path if path.exists() else None
