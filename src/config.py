import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Authentication
AUTH_MODE = os.getenv('AUTH_MODE', 'oauth')
OAUTH_CREDENTIALS_PATH = PROJECT_ROOT / os.getenv('OAUTH_CREDENTIALS_PATH', 'credentials/oauth_credentials.json')
OAUTH_TOKEN_PATH = PROJECT_ROOT / os.getenv('OAUTH_TOKEN_PATH', 'credentials/token.json')
SERVICE_ACCOUNT_PATH = PROJECT_ROOT / os.getenv('SERVICE_ACCOUNT_PATH', 'credentials/service_account.json')

# Google API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Google Sheets
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '')
SHEET_EN = os.getenv('SHEET_EN', 'Applications_EN')
SHEET_FR = os.getenv('SHEET_FR', 'Applications_FR')
SHEET_ACTIVITY = os.getenv('SHEET_ACTIVITY', 'Activity_Log')

# Email Configuration
GMAIL_USER_EMAIL = os.getenv('GMAIL_USER_EMAIL', '')
DEFAULT_DELAY_BETWEEN_EMAILS = int(os.getenv('DEFAULT_DELAY_BETWEEN_EMAILS', '2'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Follow-up Configuration
FOLLOWUP_DAYS = int(os.getenv('FOLLOWUP_DAYS', '7'))
TIMEZONE = os.getenv('TIMEZONE', 'UTC')

# Attachment Folders
ATTACHMENT_FOLDER_EN = PROJECT_ROOT / os.getenv('ATTACHMENT_FOLDER_EN', 'attachments/en')
ATTACHMENT_FOLDER_FR = PROJECT_ROOT / os.getenv('ATTACHMENT_FOLDER_FR', 'attachments/fr')

# Default values
DEFAULTS = {
    'en': {
        'company_unknown': 'Unknown Company',
        'company_placeholder': 'your company',
        'position': 'Instrumentation Engineer',
        'body': '''Dear Hiring Manager,

I am writing to express my interest in the [Position] position at [Company]. With my background in instrumentation engineering and control systems, I believe I would be a valuable addition to your team.

My experience includes:
- Designing and implementing control systems for industrial processes
- Troubleshooting and maintaining instrumentation equipment
- Collaborating with cross-functional teams to optimize system performance

I have attached my CV for your review. I would welcome the opportunity to discuss how my skills and experience align with your needs.

Thank you for your consideration.

Best regards'''
    },
    'fr': {
        'company_unknown': 'Entreprise inconnue',
        'company_placeholder': 'votre entreprise',
        'position': 'Ingénieur en Instrumentation',
        'body': '''Madame, Monsieur,

Je vous écris pour exprimer mon intérêt pour le poste de [Position] chez [Company]. Fort de mon expérience en ingénierie d'instrumentation et en systèmes de contrôle, je suis convaincu de pouvoir apporter une contribution significative à votre équipe.

Mon expérience comprend :
- Conception et mise en œuvre de systèmes de contrôle pour les processus industriels
- Dépannage et maintenance d'équipements d'instrumentation
- Collaboration avec des équipes interfonctionnelles pour optimiser les performances des systèmes

Vous trouverez mon CV en pièce jointe. Je serais ravi de discuter de la façon dont mes compétences correspondent à vos besoins.

Je vous remercie de l'attention que vous porterez à ma candidature.

Cordialement'''
    }
}