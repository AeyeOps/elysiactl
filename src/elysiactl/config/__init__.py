# Configuration management for elysiactl
from .settings import config


def get_config():
    """Get the global configuration instance."""
    return config
