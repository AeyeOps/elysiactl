"""Configuration management for elysiactl.

This module provides a centralized configuration system using environment variables
as the foundation, with sensible defaults to maintain backwards compatibility.

Phase 2: Environment Variable Foundation
- Service URLs and endpoints
- Processing constants (batch sizes, limits, timeouts)
- Collection and replication settings
- Repository paths

Future phases will layer config files and command generalization on this base.
"""

import os
from dataclasses import dataclass, field

# Load environment variables from .env file with override=True
try:
    from dotenv import load_dotenv

    # Load .env file and override existing environment variables
    load_dotenv(override=True)
except ImportError:
    # python-dotenv not installed, continue with os.getenv
    pass


def _require_env(var_name: str, fallback_var: str | None = None) -> str:
    """Require an environment variable or raise an error."""
    value = os.getenv(var_name)
    if value:
        return value
    if fallback_var:
        value = os.getenv(fallback_var)
        if value:
            return value
        raise ValueError(f"{var_name} or {fallback_var} environment variable must be set")
    raise ValueError(f"{var_name} environment variable must be set")


@dataclass
class ServiceConfig:
    """Configuration for service endpoints and connections."""

    # Weaviate service configuration
    # Check WCD_URL first (what elysia uses), then WEAVIATE_URL as fallback
    WCD_URL: str = field(default_factory=lambda: _require_env("WCD_URL", "WEAVIATE_URL"))
    weaviate_api_version: str = field(
        default_factory=lambda: os.getenv("WEAVIATE_API_VERSION", "v1")
    )

    # Elysia service configuration
    elysia_url: str = field(default_factory=lambda: _require_env("ELYSIA_URL"))
    elysia_api_version: str = field(default_factory=lambda: os.getenv("ELYSIA_API_VERSION", "v1"))

    @property
    def weaviate_base_url(self) -> str:
        """Get the base Weaviate API URL."""
        return f"{self.WCD_URL}/{self.weaviate_api_version}"

    @property
    def weaviate_scheme(self) -> str:
        """Extract scheme from Weaviate URL."""
        from urllib.parse import urlparse

        parsed = urlparse(self.WCD_URL)
        if not parsed.scheme:
            raise ValueError(f"Cannot extract scheme from Weaviate URL: {self.WCD_URL}")
        return parsed.scheme

    @property
    def weaviate_hostname(self) -> str:
        """Extract hostname from Weaviate URL."""
        from urllib.parse import urlparse

        parsed = urlparse(self.WCD_URL)
        if not parsed.hostname:
            raise ValueError(f"Cannot extract hostname from Weaviate URL: {self.WCD_URL}")
        return parsed.hostname

    @property
    def weaviate_port(self) -> int:
        """Extract port from Weaviate URL."""
        from urllib.parse import urlparse

        parsed = urlparse(self.WCD_URL)
        if not parsed.port:
            raise ValueError(
                f"Port not specified in Weaviate URL: {self.WCD_URL}. URL must include port (e.g., http://host:8080)"
            )
        return parsed.port

    @property
    def elysia_scheme(self) -> str:
        """Extract scheme from Elysia URL."""
        from urllib.parse import urlparse

        parsed = urlparse(self.elysia_url)
        if not parsed.scheme:
            raise ValueError(f"Cannot extract scheme from Elysia URL: {self.elysia_url}")
        return parsed.scheme

    @property
    def elysia_port(self) -> int:
        """Extract port from Elysia URL."""
        from urllib.parse import urlparse

        parsed = urlparse(self.elysia_url)
        if not parsed.port:
            raise ValueError(
                f"Port not specified in Elysia URL: {self.elysia_url}. URL must include port (e.g., http://host:8000)"
            )
        return parsed.port

    @property
    def weaviate_cluster_ports(self) -> list[int]:
        """Get configured Weaviate cluster ports."""
        # Require explicit configuration - no guessing
        ports_str = os.getenv("WEAVIATE_CLUSTER_PORTS", "")
        if not ports_str:
            raise ValueError(
                "WEAVIATE_CLUSTER_PORTS environment variable must be set (e.g., '8080' or '8080,8081,8082')"
            )

        try:
            return [int(p.strip()) for p in ports_str.split(",")]
        except ValueError as e:
            raise ValueError(
                f"Invalid WEAVIATE_CLUSTER_PORTS format: {ports_str}. Must be comma-separated integers."
            ) from e


@dataclass
class ProcessingConfig:
    """Configuration for processing limits and performance tuning."""

    # Batch processing
    batch_size: int = field(default_factory=lambda: int(os.getenv("ELYSIACTL_BATCH_SIZE", "100")))

    # File size limits (in bytes)
    max_file_size: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MAX_FILE_SIZE", "1000000"))
    )  # 1MB
    max_content_size: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MAX_CONTENT_SIZE", "500000"))
    )  # 500KB

    # HTTP timeouts (in seconds)
    short_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_SHORT_TIMEOUT", "5.0"))
    )
    medium_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_MEDIUM_TIMEOUT", "30.0"))
    )
    long_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_LONG_TIMEOUT", "60.0"))
    )

    # Process timeouts
    process_timeout: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_PROCESS_TIMEOUT", "5"))
    )

    # Checkpoint system settings
    checkpoint_db_dir: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_CHECKPOINT_DB_DIR", "/tmp/elysiactl")
    )
    max_retry_attempts: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MAX_RETRY_ATTEMPTS", "3"))
    )
    checkpoint_cleanup_days: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_CHECKPOINT_CLEANUP_DAYS", "7"))
    )
    sqlite_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_SQLITE_TIMEOUT", "30.0"))
    )

    # mgit tier thresholds (for analysis compatibility)
    mgit_tier_1_max: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MGIT_TIER_1_MAX", "10000"))
    )  # 10KB
    mgit_tier_2_max: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MGIT_TIER_2_MAX", "100000"))
    )  # 100KB
    mgit_tier_3_max: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MGIT_TIER_3_MAX", "10000000"))
    )  # 10MB

    # Content analysis settings
    use_mime_detection: bool = field(
        default_factory=lambda: os.getenv("ELYSIACTL_USE_MIME_DETECTION", "true").lower() == "true"
    )
    analyze_vendor_dirs: bool = field(
        default_factory=lambda: os.getenv("ELYSIACTL_ANALYZE_VENDOR_DIRS", "true").lower() == "true"
    )

    # Content resolution timeouts
    file_read_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_FILE_READ_TIMEOUT", "30.0"))
    )
    base64_decode_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_BASE64_TIMEOUT", "10.0"))
    )

    # Custom patterns (comma-separated)
    custom_skip_paths: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_CUSTOM_SKIP_PATHS", "")
    )
    custom_binary_extensions: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_CUSTOM_BINARY_EXTENSIONS", "")
    )

    # Error handling configuration
    max_retry_attempts: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MAX_RETRY_ATTEMPTS", "3"))
    )
    retry_base_delay: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_RETRY_BASE_DELAY", "1.0"))
    )
    retry_max_delay: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_RETRY_MAX_DELAY", "60.0"))
    )

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_CB_FAILURE_THRESHOLD", "5"))
    )
    circuit_breaker_recovery_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_CB_RECOVERY_TIMEOUT", "30.0"))
    )

    # Error tracking
    error_history_limit: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_ERROR_HISTORY_LIMIT", "100"))
    )
    log_level: str = field(default_factory=lambda: os.getenv("ELYSIACTL_LOG_LEVEL", "INFO"))

    # Performance optimization settings
    max_workers: int = field(default_factory=lambda: int(os.getenv("ELYSIACTL_MAX_WORKERS", "8")))
    max_connections: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MAX_CONNECTIONS", "20"))
    )
    connection_timeout: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_CONNECTION_TIMEOUT", "30.0"))
    )

    # Memory management
    memory_limit_mb: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_MEMORY_LIMIT_MB", "512"))
    )
    streaming_buffer_size: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_STREAMING_BUFFER_SIZE", "1000"))
    )

    # Batch optimization
    enable_batch_operations: bool = field(
        default_factory=lambda: os.getenv("ELYSIACTL_ENABLE_BATCH_OPERATIONS", "true").lower()
        == "true"
    )
    batch_flush_interval: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_BATCH_FLUSH_INTERVAL", "5.0"))
    )

    # Performance monitoring
    enable_metrics: bool = field(
        default_factory=lambda: os.getenv("ELYSIACTL_ENABLE_METRICS", "true").lower() == "true"
    )
    metrics_interval: float = field(
        default_factory=lambda: float(os.getenv("ELYSIACTL_METRICS_INTERVAL", "10.0"))
    )


@dataclass
class CollectionConfig:
    """Configuration for Weaviate collections and replication."""

    # Default collection names
    default_source_collection: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_DEFAULT_SOURCE_COLLECTION", "SRC_ENTERPRISE__")
    )

    # Replication settings
    replication_factor: int = field(
        default_factory=lambda: int(os.getenv("ELYSIACTL_REPLICATION_FACTOR", "3"))
    )
    replication_async_enabled: bool = field(
        default_factory=lambda: os.getenv("ELYSIACTL_REPLICATION_ASYNC", "true").lower() == "true"
    )

    # Vectorization settings
    vectorizer: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_VECTORIZER", "text2vec-openai")
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_EMBEDDING_MODEL", "text-embedding-3-small")
    )


@dataclass
class RepositoryConfig:
    """Configuration for source code repository indexing."""

    # Base paths
    enterprise_dir: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_ENTERPRISE_DIR", "/opt/pdi/Enterprise")
    )

    # Repository filtering
    repo_pattern: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_REPO_PATTERN", "https-pdidev.visualstudio")
    )
    exclude_pattern: str = field(
        default_factory=lambda: os.getenv("ELYSIACTL_EXCLUDE_PATTERN", "ZZ_Obsolete")
    )

    # Repository name cleanup
    cleanup_pattern: str = field(
        default_factory=lambda: os.getenv(
            "ELYSIACTL_CLEANUP_PATTERN", "https-pdidev.visualstudio.com-DefaultCollection-PDI-_git-"
        )
    )


@dataclass
class elysiactlConfig:
    """Main configuration container for elysiactl."""

    services: ServiceConfig = field(default_factory=ServiceConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    collections: CollectionConfig = field(default_factory=CollectionConfig)
    repositories: RepositoryConfig = field(default_factory=RepositoryConfig)

    # Global settings
    debug: bool = field(
        default_factory=lambda: os.getenv("ELYSIACTL_DEBUG", "false").lower() == "true"
    )
    verbose: bool = field(
        default_factory=lambda: os.getenv("ELYSIACTL_VERBOSE", "false").lower() == "true"
    )


# Global configuration instance
_config: elysiactlConfig | None = None


def get_config() -> elysiactlConfig:
    """Get the global configuration instance.

    Creates the configuration on first access, reading from environment variables.
    Subsequent calls return the same instance for consistency within a session.
    """
    global _config
    if _config is None:
        _config = elysiactlConfig()
    return _config


def reload_config() -> elysiactlConfig:
    """Reload configuration from environment variables.

    Useful for testing or when environment variables change during execution.
    """
    global _config
    _config = elysiactlConfig()
    return _config


# Convenience functions for common access patterns
def WCD_URL() -> str:
    """Get the Weaviate base URL."""
    return get_config().services.WCD_URL


def weaviate_api_url() -> str:
    """Get the full Weaviate API URL."""
    return get_config().services.weaviate_base_url


def batch_size() -> int:
    """Get the batch processing size."""
    return get_config().processing.batch_size


def replication_factor() -> int:
    """Get the collection replication factor."""
    return get_config().collections.replication_factor


def enterprise_dir() -> str:
    """Get the Enterprise repositories directory."""
    return get_config().repositories.enterprise_dir
