# src/monitoring.py - Enhanced version with better tracking
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import deque
import pytz
from src.config import TIMEZONE
from settings_manager import settings_manager
from src.utils import get_active_timezone


class SystemMonitor:
    def __init__(self):
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.api_calls = {
            'gmail': deque(maxlen=100),
            'sheets': deque(maxlen=100)
        }
        self.startup_time = datetime.now(get_active_timezone())

        # Log initial startup
        self.log_event('system', 'info', 'JobFlow system started', {
            'timestamp': self.startup_time.isoformat()
        })

    def log_event(self, event_type: str, severity: str, message: str, details: Dict = None):
        """Log a system event.

        Args:
            event_type: Type of event (e.g., 'email_sent', 'error', 'system')
            severity: 'info', 'warning', 'error', 'critical'
            message: Human-readable message
            details: Additional context data
        """
        tz = get_active_timezone()
        event = {
            'timestamp': datetime.now(tz).isoformat(),
            'type': event_type,
            'severity': severity,
            'message': message,
            'details': details or {}
        }
        self.events.append(event)

        # Print to console for debugging
        emoji = {'info': 'ℹ️', 'warning': '⚠️', 'error': '❌', 'critical': '🔥'}
        print(f"{emoji.get(severity, 'ℹ️')} [{severity.upper()}] {event_type}: {message}")

    def log_api_call(self, api: str, endpoint: str, success: bool, duration_ms: float):
        """Log an API call for performance tracking."""
        tz = get_active_timezone()
        call = {
            'timestamp': datetime.now(tz).isoformat(),
            'endpoint': endpoint,
            'success': success,
            'duration_ms': duration_ms
        }
        self.api_calls[api].append(call)

        # Log slow calls as warnings
        if duration_ms > 3000:  # 3 seconds
            self.log_event(f'{api}_api', 'warning',
                           f'Slow API call to {endpoint}',
                           {'duration_ms': duration_ms})

    def get_recent_events(self, limit: int = 50, severity: str = None) -> List[Dict]:
        """Get recent events, optionally filtered by severity."""
        events = list(self.events)

        if severity:
            events = [e for e in events if e['severity'] == severity]

        # Return most recent first
        return list(reversed(events[-limit:]))

    def get_api_stats(self, api: str, minutes: int = 60) -> Dict[str, Any]:
        """Get API statistics for the last N minutes."""
        cutoff = datetime.now(get_active_timezone()) - timedelta(minutes=minutes)

        calls = list(self.api_calls.get(api, []))
        recent_calls = [
            c for c in calls
            if datetime.fromisoformat(c['timestamp']) > cutoff
        ]

        if not recent_calls:
            return {
                'total_calls': 0,
                'success_rate': 100.0,  # No calls = no failures
                'avg_duration_ms': 0,
                'errors': 0
            }

        total = len(recent_calls)
        successes = sum(1 for c in recent_calls if c['success'])
        avg_duration = sum(c['duration_ms'] for c in recent_calls) / total

        return {
            'total_calls': total,
            'success_rate': (successes / total * 100) if total > 0 else 100.0,
            'avg_duration_ms': round(avg_duration, 2),
            'errors': total - successes
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Calculate overall system health based on recent activity."""
        # Check recent errors (last 100 events)
        recent_events = list(self.events)[-100:]
        recent_errors = [e for e in recent_events if e['severity'] in ['error', 'critical']]
        recent_warnings = [e for e in recent_events if e['severity'] == 'warning']

        # API health
        gmail_stats = self.get_api_stats('gmail', 30)
        sheets_stats = self.get_api_stats('sheets', 30)

        # Calculate uptime
        uptime = datetime.now(get_active_timezone()) - self.startup_time
        uptime_str = self._format_uptime(uptime)

        # Determine overall status
        critical_count = len([e for e in recent_errors if e['severity'] == 'critical'])
        error_count = len(recent_errors)
        warning_count = len(recent_warnings)

        if critical_count > 0 or error_count > 10:
            status = 'critical'
            message = f'{critical_count} critical issues, {error_count} errors detected'
        elif error_count > 5 or warning_count > 15:
            status = 'warning'
            message = f'{error_count} errors, {warning_count} warnings detected'
        elif gmail_stats['success_rate'] < 80 or sheets_stats['success_rate'] < 80:
            status = 'warning'
            message = 'API performance degraded'
        else:
            status = 'healthy'
            message = 'All systems operational'

        return {
            'status': status,
            'message': message,
            'recent_errors': len(recent_errors),
            'recent_warnings': len(recent_warnings),
            'gmail_health': gmail_stats,
            'sheets_health': sheets_stats,
            'uptime': uptime_str
        }

    def _format_uptime(self, uptime: timedelta) -> str:
        """Format uptime as human-readable string."""
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if not parts:  # Less than a minute
            parts.append(f"{seconds}s")

        return " ".join(parts)

    def clear_old_events(self, days: int = 7):
        """Clear events older than N days."""
        cutoff = datetime.now(get_active_timezone()) - timedelta(days=days)

        # Filter events
        self.events = deque(
            [e for e in self.events if datetime.fromisoformat(e['timestamp']) > cutoff],
            maxlen=1000
        )

        self.log_event('system', 'info', f'Cleared events older than {days} days')


# Global instance
system_monitor = SystemMonitor()