"""Collection management service for Weaviate collections."""

import httpx
import fnmatch
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..config import get_config
from ..services.weaviate import WeaviateService


class CollectionError(Exception):
    """Base exception for collection operations."""
    pass


class CollectionNotFoundError(CollectionError):
    """Collection does not exist."""
    pass


class CollectionProtectedError(CollectionError):
    """Collection is protected from modification."""
    pass


class CollectionExistsError(CollectionError):
    """Collection already exists."""
    pass


class WeaviateCollectionManager:
    """Manage Weaviate collections through REST API."""

    def __init__(self, base_url: str = None):
        config = get_config()
        self.base_url = base_url or config.services.weaviate_base_url.rstrip('/v1')
        self.client = httpx.Client(timeout=30.0)
        self.config = config

    def list_collections(self, filter_pattern: str = None) -> List[Dict[str, Any]]:
        """Get all collections from Weaviate with optional filtering."""
        response = self.client.get(f"{self.base_url}/v1/schema")
        response.raise_for_status()

        classes = response.json().get("classes", [])

        # Enrich with object counts and filter if requested
        enriched_classes = []
        for cls in classes:
            if filter_pattern and not fnmatch.fnmatch(cls["class"], filter_pattern):
                continue

            enriched_cls = cls.copy()
            enriched_cls["object_count"] = self.get_object_count(cls["class"])
            enriched_classes.append(enriched_cls)

        return enriched_classes

    def get_collection(self, name: str) -> Dict[str, Any]:
        """Get specific collection details."""
        response = self.client.get(f"{self.base_url}/v1/schema/{name}")
        if response.status_code == 404:
            raise CollectionNotFoundError(f"Collection '{name}' not found")
        response.raise_for_status()
        return response.json()

    def get_object_count(self, class_name: str) -> int:
        """Get object count for a collection."""
        try:
            response = self.client.get(
                f"{self.base_url}/v1/objects",
                params={"class": class_name, "limit": 0}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("totalResults", 0)
        except Exception:
            return 0

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        response = self.client.delete(f"{self.base_url}/v1/schema/{name}")
        return response.status_code == 200

    def create_collection(self, schema: dict) -> bool:
        """Create a new collection."""
        response = self.client.post(
            f"{self.base_url}/v1/schema",
            json=schema
        )
        response.raise_for_status()
        return response.status_code == 200

    def is_protected(self, collection_name: str) -> bool:
        """Check if collection matches protected patterns."""
        # Load protected patterns from config
        try:
            config_path = Path(__file__).parent / "config" / "collection_config.yaml"
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                protected_patterns = config.get("collection_management", {}).get("protected_patterns", [])
            else:
                # Fallback to hardcoded patterns
                protected_patterns = [
                    "ELYSIA_*",
                    "*_SYSTEM",
                    ".internal*",
                ]
        except Exception:
            # Fallback if config loading fails
            protected_patterns = [
                "ELYSIA_*",
                "*_SYSTEM",
                ".internal*",
            ]

        for pattern in protected_patterns:
            if fnmatch.fnmatch(collection_name, pattern):
                return True
        return False

    def get_collection_info(self, name: str) -> Dict[str, Any]:
        """Get comprehensive collection information."""
        collection = self.get_collection(name)
        object_count = self.get_object_count(name)

        return {
            "name": name,
            "object_count": object_count,
            "replicas": collection.get("replicationConfig", {}).get("factor", 1),
            "shards": collection.get("shardingConfig", {}).get("desiredCount", 1),
            "vectorizer": collection.get("vectorizer", "unknown"),
            "properties": len(collection.get("properties", [])),
            "protected": self.is_protected(name)
        }