"""
Configuration management.
Loads API key from .env, environment variables, or ~/.config/shodan-tui/config.env
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


@dataclass
class Config:
    api_key: str
    user_scripts_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "shodan-tui" / "scripts")
    exports_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "shodan-tui" / "exports")
    workspace_file: Path = field(default_factory=lambda: Path.home() / ".config" / "shodan-tui" / "workspace.json")
    history_file: Path = field(default_factory=lambda: Path.home() / ".config" / "shodan-tui" / "history.json")

    @classmethod
    def load(cls) -> "Config":
        """Load config from .env → env vars → ~/.config/shodan-tui/config.env"""
        # Try local .env first
        load_dotenv(Path.cwd() / ".env")

        # Fallback to user-level config
        user_config = Path.home() / ".config" / "shodan-tui" / "config.env"
        if user_config.exists():
            load_dotenv(user_config)

        api_key = os.getenv("SHODAN_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "SHODAN_API_KEY not set. Add it to .env or set it as an environment variable."
            )

        # Ensure config dirs exist
        config_dir = Path.home() / ".config" / "shodan-tui"
        scripts_dir = config_dir / "scripts"
        exports_dir = config_dir / "exports"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            api_key=api_key,
            user_scripts_dir=scripts_dir,
            exports_dir=exports_dir,
            workspace_file=config_dir / "workspace.json",
            history_file=config_dir / "history.json",
        )
