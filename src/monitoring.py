from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import deque
import pytz
from src.config import TIMEZONE


class SystemMonitor:
    def __init__(self):
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.api_calls = {
            'gmail': deque(maxlen=100),
            'sheets': deque(maxlen=100)
        }

    def log_event(self, event_type: str, severity: str, message: str, details: Dict = None):
        event = {
            'timestamp': datetime.now(pytz.timezone(TIMEZONE)).isoformat(),
            'type': event_type,
            'severity': severity,  # info, warning, error, critical
            'message': message,
            'details': details or {}
        }
        self.events.append(event)

    def log_api_call(self, api: str, endpoint: str, success: bool, duration_ms: float):
        call = {
            'timestamp': datetime.now(pytz.timezone(TIMEZONE)).isoformat(),
            'endpoint': endpoint,
            'success': success,
            'duration_ms': duration_ms
        }
        self.api_calls[api].append(call)

    def get_recent_events(self, limit: int = 50, severity: str = None) -> List[Dict]:
        events = list(self.events)

        if severity:
            events = [e for e in events if e['severity'] == severity]

        return events[-limit:]

    def get_api_stats(self, api: str, minutes: int = 60) -> Dict[str, Any]:
        cutoff = datetime.now(pytz.timezone(TIMEZONE)) - timedelta(minutes=minutes)

        calls = list(self.api_calls.get(api, []))
        recent_calls = [
            c for c in calls
            if datetime.fromisoformat(c['timestamp']) > cutoff
        ]

        if not recent_calls:
            return {
                'total_calls': 0,
                'success_rate': 0,
                'avg_duration_ms': 0,
                'errors': 0
            }

        total = len(recent_calls)
        successes = sum(1 for c in recent_calls if c['success'])
        avg_duration = sum(c['duration_ms'] for c in recent_calls) / total

        return {
            'total_calls': total,
            'success_rate': (successes / total * 100) if total > 0 else 0,
            'avg_duration_ms': round(avg_duration, 2),
            'errors': total - successes
        }

    def get_health_status(self) -> Dict[str, Any]:
        # Check recent errors
        recent_errors = [
            e for e in list(self.events)[-100:]
            if e['severity'] in ['error', 'critical']
        ]

        # API health
        gmail_stats = self.get_api_stats('gmail', 30)
        sheets_stats = self.get_api_stats('sheets', 30)

        # Overall status
        if len(recent_errors) > 10:
            status = 'critical'
        elif len(recent_errors) > 5:
            status = 'warning'
        elif gmail_stats['success_rate'] < 90 or sheets_stats['success_rate'] < 90:
            status = 'warning'
        else:
            status = 'healthy'

        return {
            'status': status,
            'recent_errors': len(recent_errors),
            'gmail_health': gmail_stats,
            'sheets_health': sheets_stats,
            'uptime': 'N/A'  # Would need separate tracking
        }


# Global instance
system_monitor = SystemMonitor()