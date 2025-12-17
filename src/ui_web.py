# src/ui_web.py
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime, timedelta
import pytz
import sys
import time
import random
import csv
import io

# Project config and settings manager
from src.config import PROJECT_ROOT, ATTACHMENT_FOLDER_EN, ATTACHMENT_FOLDER_FR
# Insert project root to import settings_manager
sys.path.insert(0, str(PROJECT_ROOT))
from settings_manager import settings_manager

from src.auth import get_authenticated_services
from src.sheets import SheetsClient, SHEET_COMPANIES, COMPANY_COLUMNS
from src.mailer import GmailMailer
from src.attachments import AttachmentSelector
from src.followup import FollowupEngine
from src.utils import (
    validate_email, get_default_body, get_default_position,
    substitute_placeholders, is_followup_due
)
from src.analytics import AnalyticsEngine
from src.templates_manager import TemplateManager
from src.monitoring import system_monitor

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
_analytics_engine = None
_template_manager = None


def get_clients():
    global _gmail_service, _sheets_service, _sheets_client, _mailer, _attachment_selector

    if _sheets_client is None:
        _gmail_service, _sheets_service = get_authenticated_services()
        _sheets_client = SheetsClient(_sheets_service)
        _mailer = GmailMailer(_gmail_service) if _gmail_service else None
        _attachment_selector = AttachmentSelector()

    return _sheets_client, _mailer, _attachment_selector


def get_analytics():
    global _analytics_engine
    if _analytics_engine is None:
        sheets_client, _, _ = get_clients()
        _analytics_engine = AnalyticsEngine(sheets_client)
    return _analytics_engine


def get_template_manager():
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager


def calculate_real_response_rate(all_apps):
    """Calculate real response rate based on actual responses."""
    if not all_apps:
        return 0

    # Count applications with positive responses
    positive_statuses = [
        'Interview', 'Call Received', 'Hired', 'Offer',
        'Interview Scheduled', 'Interview Complete'
    ]
    responded = sum(1 for app in all_apps
                   if app.get('status') in positive_statuses)
    return (responded / len(all_apps) * 100) if len(all_apps) > 0 else 0


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sheets_client, _, _ = get_clients()
    analytics = get_analytics()

    try:
        # Get all applications
        apps_en = sheets_client.get_applications_for_followup('en')
        apps_fr = sheets_client.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        # Calculate real stats
        total_applications = len(all_apps)

        # Sent today (use timezone from settings)
        timezone = settings_manager.get_setting('timezone', 'UTC')
        tz = pytz.timezone(timezone)
        today = datetime.now(tz).date()
        sent_today = sum(1 for app in all_apps
                         if app.get('sent_date') and
                         datetime.fromisoformat(app['sent_date']).date() == today)

        # Due follow-ups
        due_followups = sum(1 for app in all_apps
                            if is_followup_due(app.get('next_followup_date', '')))

        # REAL Response rate calculation
        response_rate = calculate_real_response_rate(all_apps)

        # Get timeline data (real)
        timeline = analytics.get_timeline_data(30)

        # Language distribution (real)
        lang_dist = {
            'en': len(apps_en),
            'fr': len(apps_fr)
        }

        # Top companies (real)
        company_heatmap = analytics.get_company_heatmap(5)

        # Today's activity (real)
        today_apps = [app for app in all_apps
                      if app.get('sent_date') and
                      datetime.fromisoformat(app['sent_date']).date() == today]

        # Recent applications
        recent_applications = sorted(
            all_apps,
            key=lambda x: x.get('sent_date', ''),
            reverse=True
        )[:10]

    except Exception as e:
        print(f"Error loading dashboard data: {e}")
        total_applications = 0
        sent_today = 0
        due_followups = 0
        response_rate = 0
        timeline = {'labels': [], 'data': []}
        lang_dist = {'en': 0, 'fr': 0}
        company_heatmap = []
        today_apps = []
        recent_applications = []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "total_applications": total_applications,
            "sent_today": sent_today,
            "due_followups": due_followups,
            "response_rate": round(response_rate, 1),
            "timeline": timeline,
            "lang_dist": lang_dist,
            "top_companies": company_heatmap,
            "today_apps": today_apps,
            "recent_applications": recent_applications
        }
    )


@app.get("/send", response_class=HTMLResponse)
async def send_page(
    request: Request,
    template: Optional[str] = None,
    company: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
    company_type: Optional[str] = None
):
    _, _, attachment_selector = get_clients()
    template_manager = get_template_manager()

    # Get available attachments
    attachments_en = [f.name for f in attachment_selector.get_attachments('en')]
    attachments_fr = [f.name for f in attachment_selector.get_attachments('fr')]

    # Get default language from settings
    default_language = settings_manager.get_setting('default_language', 'en')

    # Template loading
    template_body_en = None
    template_body_fr = None
    template_position_en = None
    template_position_fr = None
    template_language = default_language

    if template:
        # Load specific template from query param (format: "category:template_id")
        try:
            category, template_id = template.split(':', 1)
            template_data = template_manager.get_template(category, template_id)
            if template_data:
                template_language = template_data.get('language', 'en')
                if template_language == 'en':
                    template_body_en = template_data.get('body', '')
                    template_position_en = template_data.get('position', '')
                else:
                    template_body_fr = template_data.get('body', '')
                    template_position_fr = template_data.get('position', '')
        except Exception:
            pass  # Ignore malformed template param
    else:
        # Load default templates for both languages
        default_en = template_manager.get_default_template('application', 'en')
        default_fr = template_manager.get_default_template('application', 'fr')

        if default_en:
            template_body_en = default_en.get('body', '')
            template_position_en = default_en.get('position', '')

        if default_fr:
            template_body_fr = default_fr.get('body', '')
            template_position_fr = default_fr.get('position', '')

    # Fallback to config defaults if no templates found
    default_body_en = template_body_en or get_default_body('en')
    default_body_fr = template_body_fr or get_default_body('fr')
    default_position_en = template_position_en or get_default_position('en')
    default_position_fr = template_position_fr or get_default_position('fr')

    # --- Prefill from query params (company detail link passes these) ---
    # Use request.query_params for optional extras (attachment, position, bodies, etc.)
    query = request.query_params

    prefill_email = email or query.get('emails') or ''
    prefill_company = company or query.get('company') or ''
    prefill_phone = phone or query.get('phone') or ''
    prefill_website = website or query.get('website') or ''
    prefill_company_type = company_type or query.get('company_type') or ''

    prefill_attachment = query.get('attachment')  # single attachment name
    prefill_attachment_en = query.get('attachment_en')
    prefill_attachment_fr = query.get('attachment_fr')

    prefill_position = query.get('position') or ''
    prefill_position_en = query.get('position_en') or template_position_en or ''
    prefill_position_fr = query.get('position_fr') or template_position_fr or ''

    prefill_body = query.get('body') or ''
    prefill_body_en = query.get('body_en') or template_body_en or ''
    prefill_body_fr = query.get('body_fr') or template_body_fr or ''

    prefill_place = query.get('place') or ''
    prefill_salary = query.get('salary') or ''
    prefill_reference_link = query.get('reference_link') or ''
    prefill_notes = query.get('notes') or ''

    return templates.TemplateResponse(
        "send.html",
        {
            "request": request,
            "attachments_en": attachments_en,
            "attachments_fr": attachments_fr,
            "default_body_en": default_body_en,
            "default_body_fr": default_body_fr,
            "default_position_en": default_position_en,
            "default_position_fr": default_position_fr,
            "default_language": template_language if template else default_language,
            # Prefill values for the form
            "prefill_email": prefill_email,
            "prefill_company": prefill_company,
            "prefill_phone": prefill_phone,
            "prefill_website": prefill_website,
            "prefill_company_type": prefill_company_type,
            "prefill_attachment": prefill_attachment,
            "prefill_attachment_en": prefill_attachment_en,
            "prefill_attachment_fr": prefill_attachment_fr,
            "prefill_position": prefill_position,
            "prefill_position_en": prefill_position_en,
            "prefill_position_fr": prefill_position_fr,
            "prefill_body": prefill_body,
            "prefill_body_en": prefill_body_en,
            "prefill_body_fr": prefill_body_fr,
            "prefill_place": prefill_place,
            "prefill_salary": prefill_salary,
            "prefill_reference_link": prefill_reference_link,
            "prefill_notes": prefill_notes
        }
    )

@app.post("/send")
async def send_application(
        emails: str = Form(...),
        language: str = Form(...),
        company: Optional[str] = Form(None),
        position: Optional[str] = Form(None),
        position_en: Optional[str] = Form(None),
        position_fr: Optional[str] = Form(None),
        attachment: Optional[str] = Form(None),
        attachment_en: Optional[str] = Form(None),
        attachment_fr: Optional[str] = Form(None),
        body: Optional[str] = Form(None),
        body_en: Optional[str] = Form(None),
        body_fr: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        website: Optional[str] = Form(None),
        notes: Optional[str] = Form(None),
        company_type: Optional[str] = Form(None),
        salary: Optional[str] = Form(None),
        place: Optional[str] = Form(None),
        reference_link: Optional[str] = Form(None)
):
    sheets_client, mailer, attachment_selector = get_clients()

    if not mailer:
        raise HTTPException(status_code=500, detail="Gmail service not available")

    # Parse emails (support newline-separated lists)
    email_list = [e.strip() for e in emails.replace('\n', ',').split(',') if e.strip()]

    # Validate emails
    invalid_emails = [e for e in email_list if not validate_email(e)]
    if invalid_emails:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid emails: {', '.join(invalid_emails)}"
        )

    # Get email delay from settings (seconds)
    email_delay = settings_manager.get_setting('email_delay', 2)

    # Process languages
    languages = ['en', 'fr'] if language == 'both' else [language]

    results = []

    for lang in languages:
        # Get position
        if language == 'both':
            final_position = position_en if lang == 'en' else position_fr
        else:
            final_position = position

        if not final_position:
            final_position = get_default_position(lang)

        # Get body
        if language == 'both':
            final_body_template = body_en if lang == 'en' else body_fr
        else:
            final_body_template = body

        if not final_body_template:
            final_body_template = get_default_body(lang)

        # Get attachment
        if language == 'both':
            attachment_filename = attachment_en if lang == 'en' else attachment_fr
        else:
            attachment_filename = attachment

        if not attachment_filename:
            results.append({
                'language': lang,
                'status': 'error',
                'message': f'No attachment selected for {lang}'
            })
            continue

        attachment_path = attachment_selector.get_attachment_path(lang, attachment_filename)
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
                app_id = sheets_client.add_application(
                    email=recipient_email,
                    language=lang,
                    company=company,
                    position=final_position,
                    phone=phone,
                    website=website,
                    notes=notes,
                    status='Pending',
                    company_type=company_type,
                    salary=salary,
                    place=place,
                    reference_link=reference_link
                )

                final_body = substitute_placeholders(
                    final_body_template,
                    company,
                    final_position,
                    lang
                )

                # Use delay from settings (basic randomized delay to avoid bursts)
                time.sleep(email_delay + random.uniform(0, 1))

                # Send email via mailer (assumes GmailMailer has send_email)
                result = mailer.send_email(
                    to_email=recipient_email,
                    subject=final_position,
                    body=final_body,
                    attachment_path=attachment_path
                )

                sheets_client.update_application_sent(
                    app_id, lang, final_body, attachment_filename
                )

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
    sheets_client, _, _ = get_clients()

    try:
        applications = sheets_client.get_applications_for_followup(lang)

        if status:
            applications = [app for app in applications if app.get('status') == status]

        all_apps = sheets_client.get_applications_for_followup(lang)
        statuses = sorted(set(app.get('status', 'Unknown') for app in all_apps))

    except Exception as e:
        print(f"Applications page error: {e}")
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
            print(f"Followups retrieval error for {language}: {e}")
            pass

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
    sheets_client, mailer, attachment_selector = get_clients()

    if not mailer:
        raise HTTPException(status_code=500, detail="Gmail service not available")

    engine = FollowupEngine(sheets_client, mailer, attachment_selector)

    try:
        stats = engine.process_followups(language=language, dry_run=dry_run)
        return JSONResponse(content={'success': True, 'stats': stats})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    analytics = get_analytics()

    try:
        stats = analytics.get_dashboard_stats()
        timeline = analytics.get_timeline_data(30)
        company_heatmap = analytics.get_company_heatmap(10)
        status_dist = analytics.get_status_distribution()
        followup_data = analytics.get_followup_effectiveness()
    except Exception as e:
        print(f"Analytics error: {e}")
        stats = {'success_rate': 0, 'sent': 0, 'total_followups': 0, 'bounced': 0, 'total_applications': 1}
        timeline = {'labels': [], 'data': []}
        company_heatmap = []
        status_dist = {}
        followup_data = {'distribution': {}, 'max_followups': 0, 'avg_followups': 0}

    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "stats": stats,
            "timeline": timeline,
            "company_heatmap": company_heatmap,
            "status_distribution": status_dist,
            "followup_data": followup_data
        }
    )


@app.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    try:
        template_manager = get_template_manager()
        templates_data = template_manager.get_all_templates()
    except Exception as e:
        print(f"Template error: {e}")
        templates_data = {'application': {}, 'followup': {}}

    return templates.TemplateResponse(
        "templates_page.html",
        {
            "request": request,
            "templates": templates_data
        }
    )


@app.post("/api/templates/{category}/{template_id}")
async def save_template(
        category: str,
        template_id: str,
        name: str = Form(...),
        language: str = Form(...),
        position: Optional[str] = Form(None),
        body: str = Form(...),
        is_default: str = Form('false')
):
    template_manager = get_template_manager()

    template_data = {
        'name': name,
        'language': language,
        'body': body,
        'is_default': is_default.lower() == 'true'
    }

    if position:
        template_data['position'] = position

    template_manager.save_template(category, template_id, template_data)

    return JSONResponse(content={'success': True})


@app.delete("/api/templates/{category}/{template_id}")
async def delete_template(category: str, template_id: str):
    template_manager = get_template_manager()
    template_manager.delete_template(category, template_id)

    return JSONResponse(content={'success': True})


@app.post("/api/templates")
async def create_template(
    name: str = Form(...),
    language: str = Form(...),
    category: str = Form(...),
    body: str = Form(...)
):
    """Create a new template."""
    template_manager = get_template_manager()

    try:
        # Generate ID from name
        template_id = name.lower().replace(' ', '_').replace('-', '_')

        template_data = {
            'name': name,
            'language': language,
            'body': body
        }

        template_manager.save_template(category, template_id, template_data)

        return JSONResponse(content={'success': True, 'id': template_id})

    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.post("/api/settings/export")
async def export_data():
    sheets_client, _, _ = get_clients()

    try:
        apps_en = sheets_client.get_applications_for_followup('en')
        apps_fr = sheets_client.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_apps[0].keys() if all_apps else [])
        writer.writeheader()
        writer.writerows(all_apps)

        csv_content = output.getvalue()

        return JSONResponse(content={
            'success': True,
            'data': csv_content,
            'filename': f'applications_export_{datetime.now().strftime("%Y%m%d")}.csv'
        })
    except Exception as e:
        return JSONResponse(content={'success': False, 'error': str(e)})


@app.post("/api/settings/clear")
async def clear_data():
    # This is a dangerous operation - require confirmation
    return JSONResponse(content={'success': False, 'error': 'Not implemented for safety'})


@app.get("/api/attachments/{language}")
async def get_attachments(language: str):
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
    folder = ATTACHMENT_FOLDER_EN if language == 'en' else ATTACHMENT_FOLDER_FR
    folder.mkdir(parents=True, exist_ok=True)

    file_path = folder / file.filename

    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)

    return JSONResponse(content={
        'success': True,
        'filename': file.filename,
        'message': f'Uploaded to {language} folder'
    })


@app.post("/api/companies/initialize")
async def initialize_companies_sheet():
    """Initialize the Companies sheet with proper headers."""
    sheets_client, _, _ = get_clients()

    try:
        # Initialize just the Companies sheet
        sheets_client._ensure_headers(SHEET_COMPANIES, COMPANY_COLUMNS)

        return JSONResponse(content={
            'success': True,
            'message': 'Companies sheet initialized successfully'
        })
    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.get("/companies", response_class=HTMLResponse)
async def companies_page(request: Request):
    """Companies management page."""
    sheets_client, _, _ = get_clients()

    try:
        # Auto-initialize sheets (safe, idempotent)
        try:
            sheets_client.initialize_sheets()
        except Exception as e:
            # Non-fatal: log and continue
            print(f"Warning: failed to auto-initialize sheets: {e}")

        companies = sheets_client.get_all_companies()

        # Calculate recent count (this month)
        timezone = settings_manager.get_setting('timezone', 'UTC')
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        recent_count = sum(
            1 for company in companies
            if company.get('added_date') and
            datetime.fromisoformat(company['added_date']) >= first_day_of_month
        )

    except Exception as e:
        print(f"Companies page error: {e}")
        # Return empty state instead of crashing
        companies = []
        recent_count = 0

    return templates.TemplateResponse(
        "companies.html",
        {
            "request": request,
            "companies": companies,
            "recent_count": recent_count
        }
    )


@app.post("/api/companies")
async def create_company(
        name: str = Form(...),
        type: Optional[str] = Form(None),
        email: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        website: Optional[str] = Form(None),
        location: Optional[str] = Form(None),
        notes: Optional[str] = Form(None)
):
    """Create a new company and return the created company object."""
    sheets_client, _, _ = get_clients()

    try:
        company_id = sheets_client.add_company(
            company_name=name,
            company_type=type,
            email=email,
            phone=phone,
            website=website,
            location=location,
            notes=notes
        )

        # Read back the created company so frontend can update without reload
        created = sheets_client.get_company_by_id(company_id)

        return JSONResponse(content={
            'success': True,
            'company_id': company_id,
            'company': created,
            'message': 'Company added successfully'
        })
    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.get("/api/companies/{company_id}")
async def get_company(company_id: str):
    """Get a specific company by ID."""
    sheets_client, _, _ = get_clients()

    try:
        company = sheets_client.get_company_by_id(company_id)

        if company:
            return JSONResponse(content={
                'success': True,
                'company': company
            })
        else:
            return JSONResponse(
                content={'success': False, 'error': 'Company not found'},
                status_code=404
            )
    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.put("/api/companies/{company_id}")
async def update_company(
        company_id: str,
        name: str = Form(...),
        type: Optional[str] = Form(None),
        email: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        website: Optional[str] = Form(None),
        location: Optional[str] = Form(None),
        notes: Optional[str] = Form(None)
):
    """Update an existing company."""
    sheets_client, _, _ = get_clients()

    try:
        success = sheets_client.update_company(
            company_id=company_id,
            company_name=name,
            company_type=type,
            email=email,
            phone=phone,
            website=website,
            location=location,
            notes=notes
        )

        if success:
            return JSONResponse(content={
                'success': True,
                'message': 'Company updated successfully'
            })
        else:
            return JSONResponse(
                content={'success': False, 'error': 'Company not found'},
                status_code=404
            )
    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.delete("/api/companies/{company_id}")
async def delete_company(company_id: str):
    """Delete a company."""
    sheets_client, _, _ = get_clients()

    try:
        success = sheets_client.delete_company(company_id)

        if success:
            return JSONResponse(content={
                'success': True,
                'message': 'Company deleted successfully'
            })
        else:
            return JSONResponse(
                content={'success': False, 'error': 'Company not found'},
                status_code=404
            )
    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail_page(request: Request, company_id: str):
    """View detailed information about a specific company."""
    sheets_client, _, _ = get_clients()

    try:
        company = sheets_client.get_company_by_id(company_id)

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Get applications for this company (both EN and FR)
        apps_en = sheets_client.get_applications_for_followup('en')
        apps_fr = sheets_client.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        # Filter applications for this company
        company_apps = [
            app for app in all_apps
            if app.get('company', '').lower() == company['name'].lower()
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse(
        "company_detail.html",
        {
            "request": request,
            "company": company,
            "applications": company_apps
        }
    )


@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    sheets_client, mailer, _ = get_clients()

    try:
        # Get real API usage
        apps_en = sheets_client.get_applications_for_followup('en')
        apps_fr = sheets_client.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        # Calculate quota usage (use timezone from settings)
        timezone = settings_manager.get_setting('timezone', 'UTC')
        tz = pytz.timezone(timezone)
        today = datetime.now(tz).date()
        sent_today_count = sum(1 for app in all_apps
                               if app.get('sent_date') and
                               datetime.fromisoformat(app['sent_date']).date() == today)

        gmail_quota_used = sent_today_count
        gmail_quota_total = 250  # Gmail free tier
        gmail_quota_percent = (gmail_quota_used / gmail_quota_total * 100) if gmail_quota_total > 0 else 0

        # Sheets quota (rough estimate based on operations)
        sheets_operations_today = sent_today_count * 3  # Each send = ~3 operations
        sheets_quota_total = 500
        sheets_quota_percent = (sheets_operations_today / sheets_quota_total * 100) if sheets_quota_total > 0 else 0

    except Exception as e:
        print(f"Monitoring error: {e}")
        gmail_quota_used = 0
        gmail_quota_total = 250
        gmail_quota_percent = 0
        sheets_operations_today = 0
        sheets_quota_total = 500
        sheets_quota_percent = 0

    health = system_monitor.get_health_status()
    recent_events = system_monitor.get_recent_events(50)
    gmail_stats = system_monitor.get_api_stats('gmail', 60)
    sheets_stats = system_monitor.get_api_stats('sheets', 60)

    return templates.TemplateResponse(
        "monitoring.html",
        {
            "request": request,
            "health": health,
            "events": recent_events,
            "gmail_stats": gmail_stats,
            "sheets_stats": sheets_stats,
            "gmail_quota_used": gmail_quota_used,
            "gmail_quota_total": gmail_quota_total,
            "gmail_quota_percent": round(gmail_quota_percent, 1),
            "sheets_quota_used": sheets_operations_today,
            "sheets_quota_total": sheets_quota_total,
            "sheets_quota_percent": round(sheets_quota_percent, 1)
        }
    )


@app.get("/status/{app_id}", response_class=HTMLResponse)
async def status_page(request: Request, app_id: str, lang: str = "en"):
    sheets_client, _, _ = get_clients()

    try:
        application = sheets_client.get_application_by_id(app_id, lang)

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Available status options
    status_options = [
        'Pending', 'Sent', 'Follow-up Sent', 'Call Received',
        'Interview Scheduled', 'Interview Complete', 'Offer',
        'Hired', 'Rejected', 'Bounced', 'Failed', 'Frozen'
    ]

    return templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "application": application,
            "language": lang,
            "status_options": status_options
        }
    )


@app.put("/api/applications/{app_id}")
async def update_application(
    app_id: str,
    field: str = Form(...),
    value: str = Form(...),
    language: str = Form(...)
):
    """Update application field."""
    sheets_client, _, _ = get_clients()

    try:
        # Get current application
        app = sheets_client.get_application_by_id(app_id, language)
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        # Update based on field
        if field == 'status':
            sheets_client.update_application_status(app_id, language, value)
        elif field == 'company':
            # Update company name
            sheet_name = sheets_client._get_sheet_name(language)
            row_index = sheets_client._find_row_by_id(sheet_name, app_id)
            if row_index:
                sheets_client.service.spreadsheets().values().update(
                    spreadsheetId=sheets_client.spreadsheet_id,
                    range=f"{sheet_name}!B{row_index}",
                    valueInputOption="RAW",
                    body={"values": [[value]]}
                ).execute()
        elif field == 'email':
            # Update email
            sheet_name = sheets_client._get_sheet_name(language)
            row_index = sheets_client._find_row_by_id(sheet_name, app_id)
            if row_index:
                sheets_client.service.spreadsheets().values().update(
                    spreadsheetId=sheets_client.spreadsheet_id,
                    range=f"{sheet_name}!C{row_index}",
                    valueInputOption="RAW",
                    body={"values": [[value]]}
                ).execute()
        elif field == 'body':
            # Update body
            sheet_name = sheets_client._get_sheet_name(language)
            row_index = sheets_client._find_row_by_id(sheet_name, app_id)
            if row_index:
                sheets_client.service.spreadsheets().values().update(
                    spreadsheetId=sheets_client.spreadsheet_id,
                    range=f"{sheet_name}!K{row_index}",
                    valueInputOption="RAW",
                    body={"values": [[value]]}
                ).execute()

        sheets_client.log_activity(
            app_id, app.get('email', ''), f'field_updated_{field}', 'success', f'Updated {field} to: {value}'
        )

        return JSONResponse(content={'success': True})

    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.delete("/api/applications/{app_id}")
async def delete_application(app_id: str, language: str = Form(...)):
    """Delete an application."""
    sheets_client, _, _ = get_clients()

    try:
        sheet_name = sheets_client._get_sheet_name(language)
        row_index = sheets_client._find_row_by_id(sheet_name, app_id)

        if not row_index:
            raise HTTPException(status_code=404, detail="Application not found")

        # Delete the row
        sheets_client.service.spreadsheets().batchUpdate(
            spreadsheetId=sheets_client.spreadsheet_id,
            body={
                "requests": [{
                    "deleteDimension": {
                        "range": {
                            "sheetId": 0,  # Adjust based on your sheet structure
                            "dimension": "ROWS",
                            "startIndex": row_index - 1,
                            "endIndex": row_index
                        }
                    }
                }]
            }
        ).execute()

        return JSONResponse(content={'success': True})

    except Exception as e:
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
