from pathlib import Path
from typing import Dict, Any
import json

# Default configuration
DEFAULT_CONFIG = {
    "use_google_calendar": False,  # Toggle Google Calendar integration
    "data_dir": str(Path.home() / ".local" / "share" / "missminutes"),  # Data directory
    "config_dir": str(Path.home() / ".config" / "missminutes"),  # Config directory
    "default_schedule_days": 7,  # How many days to look ahead when scheduling
}

class Config:
    """Global configuration management"""
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from file or create default"""
        config_dir = Path(DEFAULT_CONFIG["config_dir"])
        config_file = config_dir / "config.json"

        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config or create default
        if config_file.exists():
            try:
                with open(config_file) as f:
                    self._config = {**DEFAULT_CONFIG, **json.load(f)}
            except json.JSONDecodeError:
                self._config = DEFAULT_CONFIG
        else:
            self._config = DEFAULT_CONFIG
            self.save_config()

    def save_config(self):
        """Save current configuration to file"""
        config_file = Path(self._config["config_dir"]) / "config.json"
        with open(config_file, "w") as f:
            json.dump(self._config, f, indent=2)

    def __getattr__(self, name: str) -> Any:
        """Allow accessing config values as attributes"""
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"Configuration has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        """Allow setting config values as attributes"""
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._config[name] = value
            self.save_config()

# Global config instance
config = Config() 