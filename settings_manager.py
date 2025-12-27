import json
from pathlib import Path
from typing import Dict, Any
from src.config import PROJECT_ROOT


class SettingsManager:
    """Persistent settings storage system."""

    def __init__(self):
        self.settings_dir = PROJECT_ROOT / 'settings_data'
        self.settings_dir.mkdir(exist_ok=True)
        self.settings_file = self.settings_dir / 'settings.json'
        self._load_settings()

    def _load_settings(self):
        """Load settings from file."""
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = self._get_default_settings()
            self._save_settings()

    def _save_settings(self):
        """Save settings to file."""
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings."""
        return {
            'default_language': 'en',
            'followup_days': 7,
            'timezone': 'Europe/Paris',
            'email_delay': 2,
            'max_retries': 3,
            'auto_followup': False
        }

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting."""
        return self.settings.get(key, default)

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        return self.settings.copy()

    def update_settings(self, updates: Dict[str, Any]) -> bool:
        """Update multiple settings."""
        try:
            self.settings.update(updates)
            self._save_settings()
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a single setting."""
        return self.update_settings({key: value})


# Global instance
settings_manager = SettingsManager()
