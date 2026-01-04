# src/analytics.py - Fixed and enhanced version
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
import pytz
from src.sheets import SheetsClient


class AnalyticsEngine:
    def __init__(self, sheets_client: SheetsClient):
        self.sheets = sheets_client

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        if not all_apps:
            return self._get_empty_stats()

        total = len(all_apps)

        # Count by status
        status_counts = defaultdict(int)
        for app in all_apps:
            status = app.get('status', 'Unknown')
            status_counts[status] += 1

        sent = status_counts.get('Sent', 0) + status_counts.get('Follow-up Sent', 0)
        pending = status_counts.get('Pending', 0)
        bounced = status_counts.get('Bounced', 0)
        failed = status_counts.get('Failed', 0)

        # REAL SUCCESS RATE - Count positive responses
        positive_statuses = [
            'Call Received', 'Interview Scheduled', 'Interview Complete',
            'Offer', 'Hired'
        ]
        successful = sum(status_counts.get(s, 0) for s in positive_statuses)

        # Calculate success rate only from applications that were actually sent
        applications_sent = total - pending
        success_rate = (successful / applications_sent * 100) if applications_sent > 0 else 0

        # Response rate (any response vs sent)
        responded = successful + status_counts.get('Rejected', 0)
        response_rate = (responded / applications_sent * 100) if applications_sent > 0 else 0

        # Language distribution
        lang_dist = {
            'en': len(apps_en),
            'fr': len(apps_fr)
        }

        # Follow-up stats
        total_followups = sum(int(app.get('followups', 0)) for app in all_apps)
        avg_followups = total_followups / total if total > 0 else 0

        return {
            'total_applications': total,
            'sent': sent,
            'pending': pending,
            'bounced': bounced,
            'failed': failed,
            'language_distribution': lang_dist,
            'total_followups': total_followups,
            'avg_followups': round(avg_followups, 2),
            'success_rate': round(success_rate, 1),
            'response_rate': round(response_rate, 1),
            'successful': successful,
            'responded': responded,
            'rejected': status_counts.get('Rejected', 0),
            'applications_sent': applications_sent,
            'status_counts': dict(status_counts)
        }

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure."""
        return {
            'total_applications': 0,
            'sent': 0,
            'pending': 0,
            'bounced': 0,
            'failed': 0,
            'language_distribution': {'en': 0, 'fr': 0},
            'total_followups': 0,
            'avg_followups': 0,
            'success_rate': 0,
            'response_rate': 0,
            'successful': 0,
            'responded': 0,
            'rejected': 0,
            'applications_sent': 0,
            'status_counts': {}
        }

    def get_timeline_data(self, days: int = 30) -> Dict[str, List]:
        """Get application timeline for the last N days."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        # Group by date
        date_counts = defaultdict(int)
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
                except Exception:
                    pass

        # Generate last N days
        end_date = datetime.now(tz).date()
        start_date = end_date - timedelta(days=days - 1)

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
        """Get top companies by application count."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        company_counts = defaultdict(int)

        for app in all_apps:
            company = app.get('company', '').strip()
            # Skip default/unknown companies
            if company and company.lower() not in ['unknown company', 'entreprise inconnue', '']:
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
        """Get distribution of application statuses."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        status_counts = defaultdict(int)

        for app in all_apps:
            status = app.get('status', 'Unknown')
            status_counts[status] += 1

        return dict(status_counts)

    def get_followup_effectiveness(self) -> Dict[str, Any]:
        """Analyze follow-up effectiveness."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        followup_distribution = defaultdict(int)
        followup_to_response = defaultdict(int)
        followup_to_success = defaultdict(int)

        positive_statuses = [
            'Call Received', 'Interview Scheduled', 'Interview Complete',
            'Offer', 'Hired'
        ]

        for app in all_apps:
            followups = int(app.get('followups', 0))
            status = app.get('status', 'Unknown')

            followup_distribution[followups] += 1

            # Track responses by followup count
            if status in positive_statuses or status == 'Rejected':
                followup_to_response[followups] += 1

            # Track successes by followup count
            if status in positive_statuses:
                followup_to_success[followups] += 1

        return {
            'distribution': dict(followup_distribution),
            'response_by_followup': dict(followup_to_response),
            'success_by_followup': dict(followup_to_success),
            'max_followups': max(followup_distribution.keys()) if followup_distribution else 0,
            'avg_followups': sum(k * v for k, v in followup_distribution.items()) / len(all_apps) if all_apps else 0
        }

    def get_response_breakdown(self) -> Dict[str, Any]:
        """Get detailed breakdown of responses."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        breakdown = {
            'total': len(all_apps),
            'sent': 0,
            'pending': 0,
            'call_received': 0,
            'interview_scheduled': 0,
            'interview_complete': 0,
            'offer': 0,
            'hired': 0,
            'rejected': 0,
            'bounced': 0,
            'failed': 0,
            'no_response': 0
        }

        for app in all_apps:
            status = app.get('status', 'Unknown')

            if status == 'Sent':
                breakdown['sent'] += 1
                breakdown['no_response'] += 1
            elif status == 'Follow-up Sent':
                breakdown['sent'] += 1
                breakdown['no_response'] += 1
            elif status == 'Pending':
                breakdown['pending'] += 1
            elif status == 'Call Received':
                breakdown['call_received'] += 1
            elif status == 'Interview Scheduled':
                breakdown['interview_scheduled'] += 1
            elif status == 'Interview Complete':
                breakdown['interview_complete'] += 1
            elif status == 'Offer':
                breakdown['offer'] += 1
            elif status == 'Hired':
                breakdown['hired'] += 1
            elif status == 'Rejected':
                breakdown['rejected'] += 1
            elif status == 'Bounced':
                breakdown['bounced'] += 1
            elif status == 'Failed':
                breakdown['failed'] += 1

        return breakdown

    def get_weekly_stats(self) -> Dict[str, Any]:
        """Get statistics for the current week."""
        apps_en = self.sheets.get_applications_for_followup('en')
        apps_fr = self.sheets.get_applications_for_followup('fr')
        all_apps = apps_en + apps_fr

        tz = pytz.UTC
        now = datetime.now(tz)
        week_start = now - timedelta(days=7)

        weekly_apps = []
        for app in all_apps:
            sent_date = app.get('sent_date')
            if sent_date:
                try:
                    dt = datetime.fromisoformat(sent_date)
                    if dt.tzinfo is None:
                        dt = tz.localize(dt)
                    if dt >= week_start:
                        weekly_apps.append(app)
                except Exception:
                    pass

        # Calculate stats for this week
        positive_statuses = [
            'Call Received', 'Interview Scheduled', 'Interview Complete',
            'Offer', 'Hired'
        ]

        weekly_sent = len(weekly_apps)
        weekly_success = sum(1 for app in weekly_apps if app.get('status') in positive_statuses)
        weekly_rejected = sum(1 for app in weekly_apps if app.get('status') == 'Rejected')

        return {
            'sent': weekly_sent,
            'successful': weekly_success,
            'rejected': weekly_rejected,
            'success_rate': (weekly_success / weekly_sent * 100) if weekly_sent > 0 else 0
        }