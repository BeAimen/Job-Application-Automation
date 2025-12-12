from typing import Dict, List, Optional
from pathlib import Path
import json
from src.config import PROJECT_ROOT


class TemplateManager:
    def __init__(self):
        self.templates_dir = PROJECT_ROOT / 'templates_data'
        self.templates_dir.mkdir(exist_ok=True)
        self.templates_file = self.templates_dir / 'templates.json'
        self._load_templates()

    def _load_templates(self):
        if self.templates_file.exists():
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        else:
            self.templates = self._get_default_templates()
            self._save_templates()

    def _save_templates(self):
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)

    def _get_default_templates(self) -> Dict:
        return {
            'application': {
                'generic_en': {
                    'name': 'Generic English',
                    'language': 'en',
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
                'generic_fr': {
                    'name': 'Generic French',
                    'language': 'fr',
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
                },
                'senior_engineer_en': {
                    'name': 'Senior Engineer (English)',
                    'language': 'en',
                    'position': 'Senior Instrumentation Engineer',
                    'body': '''Dear Hiring Manager,

I am excited to apply for the Senior [Position] role at [Company]. With over X years of experience in industrial automation and instrumentation, I have developed expertise in leading complex projects and mentoring engineering teams.

Key achievements:
- Led implementation of SCADA systems for Fortune 500 clients
- Reduced system downtime by 40% through predictive maintenance strategies
- Managed cross-functional teams of 10+ engineers

I am particularly drawn to [Company]'s innovative approach and would be thrilled to contribute my expertise to your continued success.

Please find my detailed CV attached. I look forward to discussing this opportunity.

Best regards'''
                }
            },
            'followup': {
                'polite_en': {
                    'name': 'Follow-up #1 - Polite',
                    'language': 'en',
                    'body': '''Dear Hiring Manager,

I hope this email finds you well. I wanted to follow up on my application for the [Position] position at [Company], which I submitted on [Date].

I remain very interested in this opportunity and would welcome the chance to discuss how my experience aligns with your team's needs.

Please let me know if you need any additional information from my end.

Thank you for your time and consideration.

Best regards'''
                },
                'assertive_en': {
                    'name': 'Follow-up #2 - Assertive',
                    'language': 'en',
                    'body': '''Dear Hiring Manager,

I am following up regarding my application for the [Position] position. I am very enthusiastic about the opportunity to join [Company] and believe my skills would be a strong match for your requirements.

I would appreciate an update on the hiring timeline and next steps. I am happy to provide any additional information or schedule a conversation at your convenience.

Looking forward to your response.

Best regards'''
                }
            }
        }

    def get_all_templates(self, category: Optional[str] = None) -> Dict:
        if category:
            return self.templates.get(category, {})
        return self.templates

    def get_template(self, category: str, template_id: str) -> Optional[Dict]:
        return self.templates.get(category, {}).get(template_id)

    def save_template(self, category: str, template_id: str, template_data: Dict):
        if category not in self.templates:
            self.templates[category] = {}

        self.templates[category][template_id] = template_data
        self._save_templates()

    def delete_template(self, category: str, template_id: str):
        if category in self.templates and template_id in self.templates[category]:
            del self.templates[category][template_id]
            self._save_templates()