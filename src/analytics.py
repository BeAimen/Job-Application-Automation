from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
import pytz
from src.sheets import SheetsClient


class AnalyticsEngine:
    def __init__(self, sheets_client: SheetsClient):
        self.sheets = sheets_client

    def get_dashboard_stats(self) -> Dict[str, Any]:
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        # Calculate stats
        total = len(all_apps)
        sent = len([a for a in all_apps if a.get('status') in ['Sent', 'Follow-up Sent']])
        pending = len([a for a in all_apps if a.get('status') == 'Pending'])
        bounced = len([a for a in all_apps if a.get('status') == 'Bounced'])

        # REAL SUCCESS RATE - Count positive responses
        successful = len([a for a in all_apps if a.get('status') in [
            'Interview Scheduled', 'Interview Complete', 'Call Received',
            'Offer', 'Hired'
        ]])
        success_rate = (successful / total * 100) if total > 0 else 0

        # Language distribution
        lang_dist = {
            'en': len(apps_en),
            'fr': len(apps_fr)
        }

        # Follow-up stats
        total_followups = sum(int(a.get('followups', 0)) for a in all_apps)

        return {
            'total_applications': total,
            'sent': sent,
            'pending': pending,
            'bounced': bounced,
            'language_distribution': lang_dist,
            'total_followups': total_followups,
            'success_rate': success_rate,
            'successful': successful
        }

    def get_timeline_data(self, days: int = 30) -> Dict[str, List]:
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        # Group by date
        date_counts = defaultdict(int)

        # Use UTC for consistent calculations
        tz = pytz.UTC

        for app in all_apps:
            sent_date = app.get('sent_date')
            if sent_date:
                try:
                    dt = datetime.fromisoformat(sent_date)
                    if dt.tzinfo is None:
                        dt = tz.localize(dt)
                    date_key = dt.date().isoformat()
                    date_counts[date_key] += 1
                except:
                    pass

        # Generate last N days
        end_date = datetime.now(tz).date()
        start_date = end_date - timedelta(days=days)

        labels = []
        data = []

        current = start_date
        while current <= end_date:
            labels.append(current.isoformat())
            data.append(date_counts.get(current.isoformat(), 0))
            current += timedelta(days=1)

        return {
            'labels': labels,
            'data': data
        }

    def get_company_heatmap(self, limit: int = 10) -> List[Dict]:
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        company_counts = defaultdict(int)

        for app in all_apps:
            company = app.get('company', 'Unknown')
            if company and company not in ['Unknown Company', 'Entreprise inconnue']:
                company_counts[company] += 1

        # Sort and limit
        sorted_companies = sorted(
            company_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {'company': company, 'count': count}
            for company, count in sorted_companies
        ]

    def get_status_distribution(self) -> Dict[str, int]:
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        status_counts = defaultdict(int)

        for app in all_apps:
            status = app.get('status', 'Unknown')
            status_counts[status] += 1

        return dict(status_counts)

    def get_followup_effectiveness(self) -> Dict[str, Any]:
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        followup_distribution = defaultdict(int)

        for app in all_apps:
            followups = int(app.get('followups', 0))
            followup_distribution[followups] += 1

        return {
            'distribution': dict(followup_distribution),
            'max_followups': max(followup_distribution.keys()) if followup_distribution else 0,
            'avg_followups': sum(k * v for k, v in followup_distribution.items()) / len(all_apps) if all_apps else 0
        }

    def get_response_breakdown(self) -> Dict[str, int]:
        """Get detailed breakdown of responses."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        breakdown = {
            'total': len(all_apps),
            'sent': len([a for a in all_apps if a.get('status') in ['Sent', 'Follow-up Sent']]),
            'call_received': len([a for a in all_apps if a.get('status') == 'Call Received']),
            'interview_scheduled': len([a for a in all_apps if a.get('status') == 'Interview Scheduled']),
            'interview_complete': len([a for a in all_apps if a.get('status') == 'Interview Complete']),
            'offer': len([a for a in all_apps if a.get('status') == 'Offer']),
            'hired': len([a for a in all_apps if a.get('status') == 'Hired']),
            'rejected': len([a for a in all_apps if a.get('status') == 'Rejected']),
            'no_response': len([a for a in all_apps if a.get('status') in ['Pending', 'Sent']])
        }

        return breakdown