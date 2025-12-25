import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------
# PROJECT ROOT
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------
# AUTHENTICATION CONFIGURATION
# ---------------------------------------------------------
AUTH_MODE = os.getenv('AUTH_MODE', 'oauth')  # oauth | service_account

OAUTH_CREDENTIALS_PATH = PROJECT_ROOT / os.getenv(
    'OAUTH_CREDENTIALS_PATH',
    'credentials/oauth_credentials.json'
)

OAUTH_TOKEN_PATH = PROJECT_ROOT / os.getenv(
    'OAUTH_TOKEN_PATH',
    'credentials/token.json'
)

SERVICE_ACCOUNT_PATH = PROJECT_ROOT / os.getenv(
    'SERVICE_ACCOUNT_PATH',
    'credentials/service_account.json'
)

# ---------------------------------------------------------
# GOOGLE API SCOPES
# ---------------------------------------------------------
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

# ---------------------------------------------------------
# GOOGLE SHEETS CONFIGURATION
# ---------------------------------------------------------
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '')

SHEET_EN = os.getenv('SHEET_EN', 'Applications_EN')
SHEET_FR = os.getenv('SHEET_FR', 'Applications_FR')
SHEET_ACTIVITY = os.getenv('SHEET_ACTIVITY', 'Activity_Log')
SHEET_COMPANIES = os.getenv('SHEET_COMPANIES', 'Companies')

# ---------------------------------------------------------
# EMAIL CONFIGURATION
# ---------------------------------------------------------
GMAIL_USER_EMAIL = os.getenv('GMAIL_USER_EMAIL', '')

DEFAULT_DELAY_BETWEEN_EMAILS = int(
    os.getenv('DEFAULT_DELAY_BETWEEN_EMAILS', '2')
)

MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# ---------------------------------------------------------
# FOLLOW-UP CONFIGURATION
# ---------------------------------------------------------
FOLLOWUP_DAYS = int(os.getenv('FOLLOWUP_DAYS', '7'))
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Paris')

# ---------------------------------------------------------
# ATTACHMENT FOLDERS
# ---------------------------------------------------------
ATTACHMENT_FOLDER_EN = PROJECT_ROOT / os.getenv(
    'ATTACHMENT_FOLDER_EN',
    'attachments/en'
)

ATTACHMENT_FOLDER_FR = PROJECT_ROOT / os.getenv(
    'ATTACHMENT_FOLDER_FR',
    'attachments/fr'
)

# ---------------------------------------------------------
# DEFAULT VALUES & EMAIL TEMPLATES
# ---------------------------------------------------------
DEFAULTS = {
    'en': {
        'company_unknown': 'Unknown Company',
        'company_placeholder': 'your company',
        'position': 'Instrumentation Engineer',

        'body': '''Dear Hiring Manager,

I am excited to apply for the [Position] role at [Company]. My hands-on experience with PLC systems, SCADA/HMI platforms, and field instrumentation aligns strongly with your operational and safety requirements.

During my internship at Sonatrach GL1K, I redesigned an industrial air dryer control system using Siemens TIA Portal and WinCC. This redesign resolved pressure instability and synchronization faults, resulting in a 20% improvement in air quality and a 15% reduction in system downtime. This project was formally validated as my engineering thesis.

I also have practical experience with HART-based calibration, loop checks, commissioning activities, and interpreting ISA-compliant P&IDs and control diagrams. My trilingual proficiency in Arabic, English, and French allows me to collaborate effectively across multicultural technical teams.

I am available immediately and highly motivated to contribute to [Company]'s standards of technical excellence, reliability, and safe field performance.

Thank you for your time and consideration.

Sincerely,  
Aimen Berkane
'''
    },

    'fr': {
        'company_unknown': 'Entreprise inconnue',
        'company_placeholder': 'votre entreprise',
        'position': 'Ingénieur en Instrumentation',

        'body': '''Madame, Monsieur,

Je souhaite vous soumettre ma candidature au poste de [Position] au sein de [Company]. Mon expérience pratique en systèmes PLC, SCADA/HMI et instrumentation industrielle correspond étroitement à vos exigences opérationnelles et de sécurité.

Lors de mon stage chez Sonatrach GL1K, j'ai repensé le système de contrôle d'un sécheur d'air industriel en utilisant Siemens TIA Portal et WinCC. Cette amélioration a permis d'éliminer les instabilités de pression et les défauts de synchronisation, aboutissant à une amélioration de 20 % de la qualité de l'air et à une réduction de 15 % des temps d'arrêt. Ce travail a été validé comme projet de fin d'études.

Je possède également une solide expérience en calibration HART, en loop checks, en mise en service ainsi qu'en lecture et interprétation de schémas P&ID conformes aux normes ISA. Ma maîtrise de l'arabe, de l'anglais et du français me permet de travailler efficacement dans des environnements techniques multiculturels.

Disponible immédiatement, je suis fortement motivé à contribuer aux standards d'excellence technique, de fiabilité et de sécurité de [Company].

Je vous remercie par avance pour l'attention portée à ma candidature.

Cordialement,  
Aimen Berkane
'''
    }
}
