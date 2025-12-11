from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime

from src.auth import get_authenticated_services
from src.sheets import SheetsClient
from src.mailer import GmailMailer
from src.attachments import AttachmentSelector
from src.followup import FollowupEngine
from src.utils import (
    validate_email, get_default_body, get_default_position,
    substitute_placeholders, is_followup_due
)
from src.config import PROJECT_ROOT, ATTACHMENT_FOLDER_EN, ATTACHMENT_FOLDER_FR

app = FastAPI(title="Job Application Automation", version="1.0.0")

# Mount static files
static_path = PROJECT_ROOT / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Setup templates
templates_path = PROJECT_ROOT / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Initialize clients (lazy loading)
_gmail_service = None
_sheets_service = None
_sheets_client = None
_mailer = None
_attachment_selector = None


def get_clients():
    """Get or initialize service clients."""
    global _gmail_service, _sheets_service, _sheets_client, _mailer, _attachment_selector

    if _sheets_client is None:
        _gmail_service, _sheets_service = get_authenticated_services()
        _sheets_client = SheetsClient(_sheets_service)
        _mailer = GmailMailer(_gmail_service) if _gmail_service else None
        _attachment_selector = AttachmentSelector()

    return _sheets_client, _mailer, _attachment_selector


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page / Dashboard."""
    sheets_client, _, _ = get_clients()

    # Get recent applications
    try:
        apps_en = sheets_client.get_applications_for_followup('en')
        apps_fr = sheets_client.get_applications_for_followup('fr')

        # Get stats
        total_applications = len(apps_en) + len(apps_fr)

        # Count due follow-ups
        due_followups = sum(1 for app in apps_en + apps_fr
                            if is_followup_due(app.get('next_followup_date', '')))

        # Get recent (last 10 from each)
        recent_applications = (apps_en[:10] + apps_fr[:10])
        recent_applications.sort(
            key=lambda x: x.get('sent_date', ''),
            reverse=True
        )
        recent_applications = recent_applications[:10]

    except Exception as e:
        total_applications = 0
        due_followups = 0
        recent_applications = []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "total_applications": total_applications,
            "due_followups": due_followups,
            "recent_applications": recent_applications
        }
    )


@app.get("/send", response_class=HTMLResponse)
async def send_page(request: Request):
    """Send application page."""
    _, _, attachment_selector = get_clients()

    # Get available attachments
    attachments_en = [f.name for f in attachment_selector.get_attachments('en')]
    attachments_fr = [f.name for f in attachment_selector.get_attachments('fr')]

    return templates.TemplateResponse(
        "send.html",
        {
            "request": request,
            "attachments_en": attachments_en,
            "attachments_fr": attachments_fr
        }
    )


@app.post("/send")
async def send_application(
        emails: str = Form(...),
        language: str = Form(...),
        company: Optional[str] = Form(None),
        position: Optional[str] = Form(None),
        attachment: str = Form(...),
        body: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        website: Optional[str] = Form(None),
        notes: Optional[str] = Form(None)
):
    """Send application emails."""
    sheets_client, mailer, attachment_selector = get_clients()

    if not mailer:
        raise HTTPException(status_code=500, detail="Gmail service not available")

    # Parse emails (comma or newline separated)
    email_list = [e.strip() for e in emails.replace('\\n', ',').split(',') if e.strip()]

    # Validate emails
    invalid_emails = [e for e in email_list if not validate_email(e)]
    if invalid_emails:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid emails: {', '.join(invalid_emails)}"
        )

    # Process languages
    languages = ['en', 'fr'] if language == 'both' else [language]

    results = []

    for lang in languages:
        # Get defaults
        final_position = position if position else get_default_position(lang)
        final_body_template = body if body else get_default_body(lang)

        # Validate attachment
        attachment_path = attachment_selector.get_attachment_path(lang, attachment)
        if not attachment_path:
            results.append({
                'language': lang,
                'status': 'error',
                'message': f'Attachment not found in {lang} folder'
            })
            continue

        # Send to each recipient
        for recipient_email in email_list:
            try:
                # Add to sheet
                app_id = sheets_client.add_application(
                    email=recipient_email,
                    language=lang,
                    company=company,
                    position=final_position,
                    phone=phone,
                    website=website,
                    notes=notes,
                    status='Pending'
                )

                # Prepare body
                final_body = substitute_placeholders(
                    final_body_template,
                    company,
                    final_position,
                    lang
                )

                # Send email
                result = mailer.send_with_delay(
                    to_email=recipient_email,
                    subject=final_position,
                    body=final_body,
                    attachment_path=attachment_path
                )

                # Update sheet
                sheets_client.update_application_sent(
                    app_id, lang, final_body, attachment
                )

                # Log activity
                sheets_client.log_activity(
                    app_id, recipient_email, 'email_sent', 'success',
                    'Sent via web UI'
                )

                results.append({
                    'language': lang,
                    'email': recipient_email,
                    'status': 'success',
                    'app_id': app_id
                })

            except Exception as e:
                results.append({
                    'language': lang,
                    'email': recipient_email,
                    'status': 'error',
                    'message': str(e)
                })

    return JSONResponse(content={'results': results})


@app.get("/applications", response_class=HTMLResponse)
async def applications_page(
        request: Request,
        lang: str = "en",
        status: Optional[str] = None
):
    """View all applications."""
    sheets_client, _, _ = get_clients()

    try:
        # Get all applications
        applications = sheets_client.get_applications_for_followup(lang)

        # Filter by status if provided
        if status:
            applications = [app for app in applications if app['status'] == status]

        # Get unique statuses for filter
        all_apps = sheets_client.get_applications_for_followup(lang)
        statuses = sorted(set(app.get('status', 'Unknown') for app in all_apps))

    except Exception as e:
        applications = []
        statuses = []

    return templates.TemplateResponse(
        "applications.html",
        {
            "request": request,
            "applications": applications,
            "current_lang": lang,
            "current_status": status,
            "statuses": statuses
        }
    )


@app.get("/followups", response_class=HTMLResponse)
async def followups_page(request: Request, lang: str = "both"):
    """Follow-ups management page."""
    sheets_client, _, _ = get_clients()

    languages = ['en', 'fr'] if lang == 'both' else [lang]

    due_applications = []

    for language in languages:
        try:
            apps = sheets_client.get_applications_for_followup(language)

            for app in apps:
                if is_followup_due(app.get('next_followup_date', '')):
                    app['language'] = language
                    due_applications.append(app)
        except Exception as e:
            pass

    # Sort by next followup date
    due_applications.sort(key=lambda x: x.get('next_followup_date', ''))

    return templates.TemplateResponse(
        "followups.html",
        {
            "request": request,
            "due_applications": due_applications,
            "current_lang": lang
        }
    )


@app.post("/followups/process")
async def process_followups(
        language: str = Form(...),
        dry_run: bool = Form(False)
):
    """Process due follow-ups."""
    sheets_client, mailer, attachment_selector = get_clients()

    if not mailer:
        raise HTTPException(status_code=500, detail="Gmail service not available")

    engine = FollowupEngine(sheets_client, mailer, attachment_selector)

    try:
        stats = engine.process_followups(language=language, dry_run=dry_run)
        return JSONResponse(content={'success': True, 'stats': stats})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{app_id}", response_class=HTMLResponse)
async def status_page(request: Request, app_id: str, lang: str = "en"):
    """View application status."""
    sheets_client, _, _ = get_clients()

    try:
        application = sheets_client.get_application_by_id(app_id, lang)

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "application": application,
            "language": lang
        }
    )


@app.get("/api/attachments/{language}")
async def get_attachments(language: str):
    """API endpoint to get available attachments."""
    _, _, attachment_selector = get_clients()

    attachments = [
        {
            'name': f.name,
            'size': f.stat().st_size,
            'modified': f.stat().st_mtime
        }
        for f in attachment_selector.get_attachments(language)
    ]

    return JSONResponse(content={'attachments': attachments})


@app.post("/api/upload-attachment")
async def upload_attachment(
        language: str = Form(...),
        file: UploadFile = File(...)
):
    """Upload a new attachment."""
    folder = ATTACHMENT_FOLDER_EN if language == 'en' else ATTACHMENT_FOLDER_FR
    folder.mkdir(parents=True, exist_ok=True)

    file_path = folder / file.filename

    # Save file
    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)

    return JSONResponse(content={
        'success': True,
        'filename': file.filename,
        'message': f'Uploaded to {language} folder'
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8000"))
    debug = os.getenv("WEB_DEBUG", "true").lower() == "true"

    uvicorn.run(
        "src.ui_web:app",
        host=host,
        port=port,
        reload=debug
    )