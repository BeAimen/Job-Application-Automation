from typing import Dict, Optional
from pathlib import Path
import json
from src.config import PROJECT_ROOT


class TemplateManager:
    def __init__(self):
        self.templates_dir = PROJECT_ROOT / "templates_data"
        self.templates_dir.mkdir(exist_ok=True)

        self.templates_file = self.templates_dir / "templates.json"
        self._load_templates()

    # ------------------------------------------------------------------
    # INTERNAL LOAD / SAVE
    # ------------------------------------------------------------------
    def _load_templates(self):
        if self.templates_file.exists():
            with open(self.templates_file, "r", encoding="utf-8") as f:
                self.templates = json.load(f)
        else:
            self.templates = self._get_default_templates()
            self._save_templates()

    def _save_templates(self):
        with open(self.templates_file, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # DEFAULT TEMPLATES
    # ------------------------------------------------------------------
    def _get_default_templates(self) -> Dict:
        return {
            "application": {
                "instrumentation_en": {
                    "name": "Instrumentation Engineer – Targeted (EN)",
                    "language": "en",
                    "position": "Instrumentation Engineer",
                    "is_default": True,
                    "body": (
                        "Dear Hiring Manager,\n\n"
                        "I am excited to apply for the [Position] role at [Company]. "
                        "My hands-on experience with PLC programming, SCADA/HMI systems, "
                        "and field instrumentation aligns strongly with industrial operations "
                        "and safety-critical environments.\n\n"
                        "During my internship at Sonatrach (GL1K), I redesigned an industrial "
                        "air dryer control system using Siemens TIA Portal and WinCC. "
                        "This redesign resolved pressure instability and synchronization faults, "
                        "resulting in a 20% improvement in compressed air quality and a 15% "
                        "reduction in system downtime. The project was validated and formalized "
                        "as my engineering thesis.\n\n"
                        "I have practical experience with HART-based calibration, loop checks, "
                        "FAT/SAT support, and interpreting P&IDs and ISA-compliant control diagrams. "
                        "I am comfortable working in field conditions and collaborating closely "
                        "with operations, maintenance, and safety teams.\n\n"
                        "Fluent in Arabic, English, and French, I communicate effectively across "
                        "technical and multicultural environments. I am available immediately "
                        "and highly motivated to contribute to [Company]'s standards of "
                        "operational excellence and safe field performance.\n\n"
                        "Sincerely,\n"
                        "Aimen Berkane"
                    ),
                },

                "instrumentation_fr": {
                    "name": "Ingénieur Instrumentation – Ciblé (FR)",
                    "language": "fr",
                    "position": "Ingénieur Instrumentation",
                    "is_default": True,
                    "body": (
                        "Madame, Monsieur,\n\n"
                        "Je souhaite vous présenter ma candidature au poste de [Position] au sein "
                        "de [Company]. Mon expérience pratique en instrumentation industrielle, "
                        "automatisme (PLC) et systèmes SCADA/HMI correspond étroitement aux "
                        "exigences des environnements industriels et pétroliers.\n\n"
                        "Lors de mon stage chez Sonatrach (GL1K), j'ai réalisé la refonte complète "
                        "du système de contrôle d'un sécheur d'air industriel à l'aide de Siemens "
                        "TIA Portal et WinCC. Cette intervention a permis de corriger des "
                        "instabilités de pression et des défauts de synchronisation, entraînant "
                        "une amélioration de 20 % de la qualité de l'air comprimé et une réduction "
                        "de 15 % des arrêts système. Ce travail a été validé comme projet de fin "
                        "d'études.\n\n"
                        "Je dispose d'une expérience terrain en calibration HART, loop checking, "
                        "assistance FAT/SAT ainsi qu'en lecture et interprétation des schémas P&ID "
                        "et normes ISA. Je suis à l'aise dans les environnements de terrain et le "
                        "travail en coordination avec les équipes exploitation, maintenance et "
                        "sécurité.\n\n"
                        "Trilingue (arabe, anglais, français), je m'intègre efficacement dans des "
                        "équipes techniques multiculturelles. Disponible immédiatement, je suis "
                        "motivé à contribuer aux standards de performance et de sécurité de "
                        "[Company].\n\n"
                        "Cordialement,\n"
                        "Aimen Berkane"
                    ),
                },
            },

            "followup": {
                "polite_en": {
                    "name": "Follow-up – Polite (EN)",
                    "language": "en",
                    "is_default": True,
                    "body": (
                        "Dear Hiring Manager,\n\n"
                        "I hope you are doing well. I am writing to follow up on my application "
                        "for the [Position] role at [Company], submitted on [Date].\n\n"
                        "I remain very interested in this opportunity and would welcome the "
                        "chance to discuss how my background could support your team.\n\n"
                        "Thank you for your time and consideration.\n\n"
                        "Best regards,\n"
                        "Aimen Berkane"
                    ),
                },

                "assertive_en": {
                    "name": "Follow-up – Assertive (EN)",
                    "language": "en",
                    "is_default": False,
                    "body": (
                        "Dear Hiring Manager,\n\n"
                        "I am following up regarding my application for the [Position] role at "
                        "[Company]. I am highly enthusiastic about the opportunity and confident "
                        "that my technical background aligns well with your requirements.\n\n"
                        "I would appreciate an update on the hiring process and next steps. "
                        "Please let me know if any additional information is needed.\n\n"
                        "Kind regards,\n"
                        "Aimen Berkane"
                    ),
                },

                "polite_fr": {
                    "name": "Follow-up – Poli (FR)",
                    "language": "fr",
                    "is_default": True,
                    "body": (
                        "Madame, Monsieur,\n\n"
                        "J'espère que vous allez bien. Je me permets de revenir vers vous "
                        "concernant ma candidature pour le poste de [Position] chez [Company].\n\n"
                        "Je reste très intéressé par cette opportunité et serais ravi de "
                        "pouvoir échanger avec vous sur la façon dont mon expérience pourrait "
                        "contribuer à votre équipe.\n\n"
                        "Je vous remercie de votre attention.\n\n"
                        "Cordialement,\n"
                        "Aimen Berkane"
                    ),
                },
            },
        }

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------
    def get_all_templates(self, category: Optional[str] = None) -> Dict:
        if category:
            return self.templates.get(category, {})
        return self.templates

    def get_template(self, category: str, template_id: str) -> Optional[Dict]:
        return self.templates.get(category, {}).get(template_id)

    def get_default_template(self, category: str, language: str) -> Optional[Dict]:
        """Get the default template for a specific category and language."""
        templates = self.templates.get(category, {})
        for template_id, template in templates.items():
            if template.get('language') == language and template.get('is_default', False):
                return {**template, 'id': template_id}
        return None

    def save_template(self, category: str, template_id: str, template_data: Dict):
        if category not in self.templates:
            self.templates[category] = {}

        # If setting as default, remove default flag from other templates with same language
        if template_data.get('is_default', False):
            language = template_data.get('language')
            for tid, tmpl in self.templates[category].items():
                if tmpl.get('language') == language and tid != template_id:
                    self.templates[category][tid]['is_default'] = False

        self.templates[category][template_id] = template_data
        self._save_templates()

    def delete_template(self, category: str, template_id: str):
        if category in self.templates and template_id in self.templates[category]:
            del self.templates[category][template_id]
            self._save_templates()