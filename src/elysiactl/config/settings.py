"""Configuration management for elysiactl."""

from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
    """Manages application configuration settings."""

    def __init__(self):
        self.config_dir = Path.home() / ".elysiactl"
        self.config_dir.mkdir(exist_ok=True)
        self.settings_file = self.config_dir / "settings.yaml"
        self._settings = {}
        self._load_settings()

    def _load_settings(self):
        """Load settings from file, with defaults."""
        # Default settings
        default_settings = {
            "sync": {
                "destination_path": "/opt/weaviate/data/repositories",
                "max_concurrent": 3,
                "sync_timeout": 300,
                "cleanup_after_ingestion": False,
            },
            "weaviate": {
                "endpoint": "http://localhost:8080",
                "batch_size": 100,
                "enable_embeddings": True,
            },
            "services": {
                "weaviate_base_url": "http://localhost:8080",
                "weaviate_scheme": "http",
                "weaviate_hostname": "localhost",
                "weaviate_port": 8080,
                "weaviate_cluster_ports": [8080, 8081, 8082],
                "elysia_url": "http://localhost:8000",
                "elysia_port": 8000,
                "elysia_scheme": "http",
                "WCD_URL": "http://localhost:8080",
            },
            "processing": {
                "batch_size": 100,
                "max_content_size": 100000,
                "max_file_size": 10000000,
                "sqlite_timeout": 30.0,
                "medium_timeout": 60.0,
                "long_timeout": 300.0,
                "checkpoint_cleanup_days": 7,
                "checkpoint_db_dir": "~/.elysiactl/checkpoints",
                "circuit_breaker_failure_threshold": 5,
                "circuit_breaker_recovery_timeout": 60,
                "retry_base_delay": 1.0,
                "retry_max_delay": 60.0,
                "mgit_tier_1_max": 10240,
                "mgit_tier_2_max": 102400,
                "mgit_tier_3_max": 10485760,
                "custom_skip_paths": "",
                "custom_binary_extensions": "",
                "analyze_vendor_dirs": False,
                "use_mime_detection": True,
            },
            "collections": {
                "default_source_collection": "SourceCode",
                "replication_factor": 3,
                "replication_async_enabled": False,
                "vectorizer": "text2vec-transformers",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            },
            "repositories": {
                "enterprise_dir": "~/.elysiactl/enterprise",
                "repo_pattern": "",
                "exclude_pattern": "",
                "cleanup_pattern": "",
            },
            "discovery": {
                "default_pattern": "*/*/*",
                "providers": [],
                "exclude_patterns": ["*/test/*", "*/tests/*", "*/*-docs"],
            },
            "tools": {"mgit_path": ""},
            "logging": {
                "level": "INFO",
                "file": "/opt/weaviate/logs/elysiactl.log",
                "max_file_size": "10MB",
                "max_files": 5,
            },
        }

        # Try to load from file
        if self.settings_file.exists():
            try:
                with open(self.settings_file) as f:
                    file_settings = yaml.safe_load(f)
                    if file_settings:
                        # Merge file settings with defaults
                        self._deep_merge(default_settings, file_settings)
            except Exception as e:
                print(f"Warning: Could not load settings file: {e}")

        self._settings = default_settings

    def _deep_merge(self, base: dict[str, Any], update: dict[str, Any]):
        """Deep merge update dict into base dict."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key."""
        keys = key.split(".")
        value = self._settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Set a configuration value by dot-notation key."""
        keys = key.split(".")
        settings = self._settings

        # Navigate to the parent dict
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]

        # Set the value
        settings[keys[-1]] = value

        # Save to file
        self._save_settings()

    def _save_settings(self):
        """Save current settings to file."""
        try:
            with open(self.settings_file, "w") as f:
                yaml.dump(self._settings, f, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save settings file: {e}")

    def get_sync_destination(self) -> str:
        """Get the configured sync destination path."""
        return self.get("sync.destination_path")

    def get_weaviate_endpoint(self) -> str:
        """Get the configured Weaviate endpoint."""
        return self.get("weaviate.endpoint")

    def get_mgit_path(self) -> str | None:
        """Get the configured mgit executable path. No fallback to PATH."""
        configured_path = self.get("tools.mgit_path")
        if configured_path and configured_path.strip():
            return configured_path.strip()
        return None

    def find_mgit_in_path(self) -> str | None:
        """Find mgit in PATH if not configured."""
        import shutil

        return shutil.which("mgit")

    def get_mgit_info(self) -> dict[str, Any]:
        """Get comprehensive mgit information including path and version."""
        info = {
            "configured_path": self.get_mgit_path(),
            "path_found": self.find_mgit_in_path(),
            "effective_path": None,
            "version": None,
            "source": None,
        }

        # Determine effective path and source
        if info["configured_path"]:
            info["effective_path"] = info["configured_path"]
            info["source"] = "configured"
        elif info["path_found"]:
            info["effective_path"] = info["path_found"]
            info["source"] = "PATH"

        # Get version if path exists
        if info["effective_path"]:
            info["version"] = self._get_mgit_version(info["effective_path"])

        return info

    def _get_mgit_version(self, mgit_path: str) -> str | None:
        """Get mgit version information."""
        try:
            import subprocess

            result = subprocess.run(
                [mgit_path, "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                # Parse version from output (format: "mgit version: 0.7.0")
                output = result.stdout.strip()
                if "version:" in output:
                    return output.split("version:")[-1].strip()
                elif "v" in output:
                    return output.split("v")[-1].split()[0]
                return output
        except Exception:
            pass
        return None


class _ConfigSection:
    """Simple object to support attribute access on config sections."""

    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name):
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return _ConfigSection(value)
            return value
        raise AttributeError(f"Config section has no attribute '{name}'")


# Add attribute access support to ConfigManager
def _config_manager_getattr(self, name):
    """Support attribute access for backward compatibility."""
    if name in self._settings:
        value = self._settings[name]
        if isinstance(value, dict):
            return _ConfigSection(value)
        return value
    raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Monkey patch the ConfigManager class
ConfigManager.__getattr__ = _config_manager_getattr


# Global config instance
config = ConfigManager()
