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
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ServiceConfig:
    """Configuration for service endpoints and connections."""
    
    # Weaviate service configuration
    weaviate_url: str = field(default_factory=lambda: os.getenv("WEAVIATE_URL", "http://localhost:8080"))
    weaviate_api_version: str = field(default_factory=lambda: os.getenv("WEAVIATE_API_VERSION", "v1"))
    
    # Elysia service configuration  
    elysia_url: str = field(default_factory=lambda: os.getenv("ELYSIA_URL", "http://localhost:8000"))
    elysia_api_version: str = field(default_factory=lambda: os.getenv("ELYSIA_API_VERSION", "v1"))
    
    @property
    def weaviate_base_url(self) -> str:
        """Get the base Weaviate API URL."""
        return f"{self.weaviate_url}/{self.weaviate_api_version}"


@dataclass  
class ProcessingConfig:
    """Configuration for processing limits and performance tuning."""
    
    # Batch processing
    batch_size: int = field(default_factory=lambda: int(os.getenv("elysiactl_BATCH_SIZE", "100")))
    
    # File size limits (in bytes)
    max_file_size: int = field(default_factory=lambda: int(os.getenv("elysiactl_MAX_FILE_SIZE", "1000000")))  # 1MB
    max_content_size: int = field(default_factory=lambda: int(os.getenv("elysiactl_MAX_CONTENT_SIZE", "500000")))  # 500KB
    
    # HTTP timeouts (in seconds)
    short_timeout: float = field(default_factory=lambda: float(os.getenv("elysiactl_SHORT_TIMEOUT", "5.0")))
    medium_timeout: float = field(default_factory=lambda: float(os.getenv("elysiactl_MEDIUM_TIMEOUT", "30.0"))) 
    long_timeout: float = field(default_factory=lambda: float(os.getenv("elysiactl_LONG_TIMEOUT", "60.0")))
    
    # Process timeouts
    process_timeout: int = field(default_factory=lambda: int(os.getenv("elysiactl_PROCESS_TIMEOUT", "5")))


@dataclass
class CollectionConfig:
    """Configuration for Weaviate collections and replication."""
    
    # Default collection names
    default_source_collection: str = field(default_factory=lambda: os.getenv("elysiactl_DEFAULT_SOURCE_COLLECTION", "SRC_ENTERPRISE__"))
    
    # Replication settings
    replication_factor: int = field(default_factory=lambda: int(os.getenv("elysiactl_REPLICATION_FACTOR", "3")))
    replication_async_enabled: bool = field(default_factory=lambda: os.getenv("elysiactl_REPLICATION_ASYNC", "true").lower() == "true")
    
    # Vectorization settings
    vectorizer: str = field(default_factory=lambda: os.getenv("elysiactl_VECTORIZER", "text2vec-openai"))
    embedding_model: str = field(default_factory=lambda: os.getenv("elysiactl_EMBEDDING_MODEL", "text-embedding-3-small"))


@dataclass
class RepositoryConfig:
    """Configuration for source code repository indexing."""
    
    # Base paths
    enterprise_dir: str = field(default_factory=lambda: os.getenv("elysiactl_ENTERPRISE_DIR", "/opt/pdi/Enterprise"))
    
    # Repository filtering
    repo_pattern: str = field(default_factory=lambda: os.getenv("elysiactl_REPO_PATTERN", "https-pdidev.visualstudio"))
    exclude_pattern: str = field(default_factory=lambda: os.getenv("elysiactl_EXCLUDE_PATTERN", "ZZ_Obsolete"))
    
    # Repository name cleanup
    cleanup_pattern: str = field(default_factory=lambda: os.getenv("elysiactl_CLEANUP_PATTERN", "https-pdidev.visualstudio.com-DefaultCollection-PDI-_git-"))


@dataclass
class elysiactlConfig:
    """Main configuration container for elysiactl."""
    
    services: ServiceConfig = field(default_factory=ServiceConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    collections: CollectionConfig = field(default_factory=CollectionConfig)
    repositories: RepositoryConfig = field(default_factory=RepositoryConfig)
    
    # Global settings
    debug: bool = field(default_factory=lambda: os.getenv("elysiactl_DEBUG", "false").lower() == "true")
    verbose: bool = field(default_factory=lambda: os.getenv("elysiactl_VERBOSE", "false").lower() == "true")


# Global configuration instance
_config: Optional[elysiactlConfig] = None


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
def weaviate_url() -> str:
    """Get the Weaviate base URL."""
    return get_config().services.weaviate_url


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


# URL replacement functions for backward compatibility during Phase 2 transition
def replace_localhost_url(url: str) -> str:
    """Replace hardcoded localhost:8080 URLs with configured Weaviate URL.
    
    This is a transitional function for Phase 2 to enable quick configuration
    updates without full command rewrites. Future phases should use direct
    config access.
    """
    if "localhost:8080" in url:
        return url.replace("http://localhost:8080/v1", weaviate_api_url())
    return url