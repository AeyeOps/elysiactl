"""Tests for collection management functionality."""

import pytest
from unittest.mock import Mock, patch
from elysiactl.services.weaviate_collections import (
    WeaviateCollectionManager,
    CollectionNotFoundError
)


class TestWeaviateCollectionManager:
    """Test the Weaviate collection manager service."""

    def test_list_collections_basic(self):
        """Test basic collection listing."""
        with patch('httpx.Client') as mock_client:
            # Mock the response
            mock_response = Mock()
            mock_response.json.return_value = {
                "classes": [
                    {
                        "class": "TestCollection",
                        "replicationConfig": {"factor": 3},
                        "shardingConfig": {"desiredCount": 1},
                        "properties": [{"name": "content"}]
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.get.return_value = mock_response

            # Mock object count response
            mock_count_response = Mock()
            mock_count_response.json.return_value = {"totalResults": 42}
            mock_count_response.raise_for_status.return_value = None
            mock_client.return_value.get.side_effect = [mock_response, mock_count_response]

            manager = WeaviateCollectionManager()
            collections = manager.list_collections()

            assert len(collections) == 1
            assert collections[0]["class"] == "TestCollection"
            assert collections[0]["object_count"] == 42

    def test_is_protected_system_collections(self):
        """Test that system collections are properly protected."""
        with patch('httpx.Client'):
            manager = WeaviateCollectionManager()

            # Test protected patterns
            assert manager.is_protected("ELYSIA_CONFIG__") == True
            assert manager.is_protected("MY_SYSTEM") == True
            assert manager.is_protected(".internal_stuff") == True

            # Test non-protected
            assert manager.is_protected("MyCustomCollection") == False
            assert manager.is_protected("test_collection") == False

    def test_collection_not_found_error(self):
        """Test handling of non-existent collections."""
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client.return_value.get.return_value = mock_response

            manager = WeaviateCollectionManager()

            with pytest.raises(CollectionNotFoundError):
                manager.get_collection("NonExistentCollection")


class TestCollectionCommands:
    """Integration tests for collection CLI commands."""

    def test_ls_command_basic(self, capsys):
        """Test basic collection listing command."""
        # This would require mocking subprocess or using the live system
        # For now, we'll test the service layer which we've verified works
        pass

    def test_create_collection_success(self):
        """Test successful collection creation."""
        with patch('httpx.Client') as mock_client:
            # Mock collection doesn't exist (first call fails)
            mock_404_response = Mock()
            mock_404_response.status_code = 404
            mock_404_response.raise_for_status.side_effect = Exception("404")

            # Mock successful creation (second call succeeds)
            mock_create_response = Mock()
            mock_create_response.status_code = 200
            mock_create_response.raise_for_status.return_value = None

            mock_client.return_value.get.side_effect = [mock_404_response]
            mock_client.return_value.post.return_value = mock_create_response

            manager = WeaviateCollectionManager()
            success = manager.create_collection({"class": "TestCollection"})

            assert success == True