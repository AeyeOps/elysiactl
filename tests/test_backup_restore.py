"""Tests for backup and restore functionality."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from elysiactl.services.backup_restore import BackupManager, RestoreManager


class TestBackupManager:
    """Test BackupManager functionality."""

    @pytest.fixture
    def backup_manager(self):
        """Create BackupManager instance."""
        return BackupManager(base_url="http://test-server:8080")

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create temporary output directory."""
        output_dir = tmp_path / "backups"
        output_dir.mkdir()
        return output_dir

    @patch('httpx.Client.get')
    def test_collection_exists_success(self, mock_get, backup_manager):
        """Test collection_exists returns True for existing collection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = backup_manager.collection_exists("TestCollection")

        assert result is True
        mock_get.assert_called_once_with("http://test-server:8080/v1/schema/TestCollection")

    @patch('httpx.Client.get')
    def test_collection_exists_not_found(self, mock_get, backup_manager):
        """Test collection_exists returns False for non-existent collection."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = backup_manager.collection_exists("NonExistentCollection")

        assert result is False

    @patch('httpx.Client.get')
    def test_get_collection_schema(self, mock_get, backup_manager):
        """Test get_collection_schema retrieves and returns schema."""
        mock_schema = {
            "class": "TestCollection",
            "properties": [
                {"name": "title", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]}
            ]
        }

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_schema
        mock_get.return_value = mock_response

        result = backup_manager.get_collection_schema("TestCollection")

        assert result == mock_schema
        mock_get.assert_called_once_with("http://test-server:8080/v1/schema/TestCollection")

    @patch('httpx.Client.get')
    def test_get_object_count(self, mock_get, backup_manager):
        """Test get_object_count retrieves object count."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"totalResults": 150}
        mock_get.return_value = mock_response

        result = backup_manager.get_object_count("TestCollection")

        assert result == 150
        mock_get.assert_called_with(
            "http://test-server:8080/v1/objects",
            params={"class": "TestCollection", "limit": 0}
        )

    @patch('httpx.Client.get')
    def test_get_object_count_error(self, mock_get, backup_manager):
        """Test get_object_count handles errors gracefully."""
        mock_get.side_effect = Exception("Connection failed")

        result = backup_manager.get_object_count("TestCollection")

        assert result == 0

    @patch('httpx.Client.get')
    def test_get_weaviate_version(self, mock_get, backup_manager):
        """Test get_weaviate_version retrieves version info."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"version": "1.23.0"}
        mock_get.return_value = mock_response

        result = backup_manager.get_weaviate_version()

        assert result == "1.23.0"
        mock_get.assert_called_once_with("http://test-server:8080/v1/meta")

    @patch('httpx.Client.get')
    def test_get_weaviate_version_error(self, mock_get, backup_manager):
        """Test get_weaviate_version handles errors."""
        mock_get.side_effect = Exception("Connection failed")

        result = backup_manager.get_weaviate_version()

        assert result == "unknown"

    def test_save_backup(self, backup_manager, temp_output_dir):
        """Test save_backup writes backup file correctly."""
        backup_data = {
            "metadata": {
                "version": "1.0",
                "timestamp": "2024-02-01T10:30:00Z",
                "collection": "TestCollection",
                "type": "schema-only"
            },
            "schema": {"class": "TestCollection"},
            "objects": []
        }

        with patch('elysiactl.services.backup_restore.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240201_103000"

            result = backup_manager.save_backup(backup_data, temp_output_dir, "TestCollection", include_data=False)

            assert result.exists()
            assert result.name.startswith("TestCollection_schema_")

            # Verify file contents
            with open(result, "r") as f:
                saved_data = json.load(f)
                assert saved_data == backup_data

    @patch('httpx.Client.get')
    def test_dry_run_backup(self, mock_get, backup_manager, temp_output_dir):
        """Test dry-run backup mode."""
        # Mock successful collection existence check
        mock_exists_response = Mock()
        mock_exists_response.status_code = 200

        # Mock schema response
        mock_schema = {
            "class": "TestCollection",
            "properties": [{"name": "title", "dataType": ["text"]}]
        }
        mock_schema_response = Mock()
        mock_schema_response.raise_for_status.return_value = None
        mock_schema_response.json.return_value = mock_schema

        # Mock object count response
        mock_count_response = Mock()
        mock_count_response.raise_for_status.return_value = None
        mock_count_response.json.return_value = {"totalResults": 25}

        # Set up mock sequence
        mock_get.side_effect = [mock_exists_response, mock_schema_response, mock_count_response]

        result = backup_manager._dry_run_backup("TestCollection", temp_output_dir)

        assert result is None
        # Verify no files were created
        assert len(list(temp_output_dir.iterdir())) == 0

    @patch('httpx.Client.get')
    def test_backup_with_data(self, mock_get, backup_manager, temp_output_dir):
        """Test backup_with_data creates full backup with objects."""
        # Mock collection existence
        mock_exists_response = Mock()
        mock_exists_response.status_code = 200
        # mock_get.return_value = mock_exists_response  # Remove conflicting assignment

        # Mock schema response
        mock_schema = {
            "class": "TestCollection",
            "properties": [{"name": "title", "dataType": ["text"]}]
        }
        mock_schema_response = Mock()
        mock_schema_response.raise_for_status.return_value = None
        mock_schema_response.json.return_value = mock_schema

        # Mock object count response
        mock_count_response = Mock()
        mock_count_response.raise_for_status.return_value = None
        mock_count_response.json.return_value = {"totalResults": 2}

        # Mock objects response
        mock_objects_response = Mock()
        mock_objects_response.raise_for_status.return_value = None
        mock_objects_response.json.return_value = {
            "objects": [
                {"id": "obj1", "properties": {"title": "Test 1"}},
                {"id": "obj2", "properties": {"title": "Test 2"}}
            ]
        }

        # Mock Weaviate version
        mock_version_response = Mock()
        mock_version_response.raise_for_status.return_value = None
        mock_version_response.json.return_value = {"version": "1.23.0"}

        # Set up mock sequence
        mock_get.side_effect = [
            mock_exists_response,  # collection_exists
            mock_schema_response,  # get_collection_schema
            mock_count_response,   # get_object_count
            mock_objects_response, # fetch objects
            mock_version_response  # get_weaviate_version
        ]

        with patch('elysiactl.services.backup_restore.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240201_103000"
            mock_datetime.now.return_value.isoformat.return_value = "2024-02-01T10:30:00Z"

            result = backup_manager.backup_with_data("TestCollection", temp_output_dir)

            assert result.exists()
            assert result.name.startswith("TestCollection_full_")

            # Verify file contents
            with open(result, "r") as f:
                saved_data = json.load(f)
                assert saved_data["metadata"]["type"] == "full-backup"
                assert len(saved_data["objects"]) == 2
                assert saved_data["objects"][0]["id"] == "obj1"

    @patch('httpx.Client.get')
    def test_fetch_all_objects(self, mock_get, backup_manager):
        """Test _fetch_all_objects fetches all objects with pagination."""
        # Mock responses for 3 batches (250 objects total)
        mock_responses = []
        for i in range(3):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            if i < 2:
                # First two batches have 100 objects
                mock_response.json.return_value = {
                    "objects": [{"id": f"obj{j}", "properties": {"title": f"Test {j}"}} for j in range(i*100, (i+1)*100)]
                }
            else:
                # Last batch has 50 objects
                mock_response.json.return_value = {
                    "objects": [{"id": f"obj{j}", "properties": {"title": f"Test {j}"}} for j in range(200, 250)]
                }
            mock_responses.append(mock_response)

        mock_get.side_effect = mock_responses

        objects = backup_manager._fetch_all_objects_streaming("TestCollection", 250, include_vectors=False)

        assert len(objects) == 250
        assert objects[0]["id"] == "obj0"
        assert objects[249]["id"] == "obj249"

        # Verify calls were made with correct offsets and include parameter
        expected_calls = [
            (("http://test-server:8080/v1/objects",), {"params": {"class": "TestCollection", "limit": 100, "offset": 0, "include": "properties"}, "timeout": 60.0}),
            (("http://test-server:8080/v1/objects",), {"params": {"class": "TestCollection", "limit": 100, "offset": 100, "include": "properties"}, "timeout": 60.0}),
            (("http://test-server:8080/v1/objects",), {"params": {"class": "TestCollection", "limit": 100, "offset": 200, "include": "properties"}, "timeout": 60.0})
        ]
        for i, call in enumerate(mock_get.call_args_list):
            assert call[0] == expected_calls[i][0]
            assert call[1] == expected_calls[i][1]

    @patch('httpx.Client.get')
    def test_dry_run_backup_with_data(self, mock_get, backup_manager, temp_output_dir):
        """Test dry-run backup with data mode."""
        # Mock successful collection existence check
        mock_exists_response = Mock()
        mock_exists_response.status_code = 200

        # Mock schema response
        mock_schema = {
            "class": "TestCollection",
            "properties": [{"name": "title", "dataType": ["text"]}]
        }
        mock_schema_response = Mock()
        mock_schema_response.raise_for_status.return_value = None
        mock_schema_response.json.return_value = mock_schema

        # Mock object count response
        mock_count_response = Mock()
        mock_count_response.raise_for_status.return_value = None
        mock_count_response.json.return_value = {"totalResults": 150}

        # Set up mock sequence
        mock_get.side_effect = [mock_exists_response, mock_schema_response, mock_count_response]

        result = backup_manager._dry_run_backup_with_data("TestCollection", temp_output_dir, include_vectors=False)

        assert result is None
        # Verify no files were created
        assert len(list(temp_output_dir.iterdir())) == 0


class TestRestoreManager:
    """Test RestoreManager functionality."""

    @pytest.fixture
    def restore_manager(self):
        """Create RestoreManager instance."""
        return RestoreManager(base_url="http://test-server:8080")

    @pytest.fixture
    def sample_backup_data(self):
        """Create sample backup data."""
        return {
            "metadata": {
                "version": "1.0",
                "timestamp": "2024-01-01T10:00:00Z",
                "collection": "TestCollection",
                "weaviate_version": "1.23.0",
                "type": "full",
                "object_count": 2
            },
            "schema": {
                "class": "TestCollection",
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Main content field"
                    }
                ],
                "replicationConfig": {"factor": 1},
                "shardingConfig": {"desiredCount": 1},
                "vectorizer": "text2vec-openai"
            },
            "objects": [
                {
                    "id": "test-id-1",
                    "class": "TestCollection",
                    "properties": {"content": "Test content 1"},
                    "vector": [0.1, 0.2, 0.3]
                },
                {
                    "id": "test-id-2",
                    "class": "TestCollection",
                    "properties": {"content": "Test content 2"},
                    "vector": [0.4, 0.5, 0.6]
                }
            ]
        }

    def test_restore_manager_init(self, restore_manager):
        """Test RestoreManager initialization."""
        assert restore_manager.base_url == "http://test-server:8080"
        assert restore_manager.client is not None

    def test_load_backup_success(self, restore_manager, tmp_path, sample_backup_data):
        """Test loading a valid backup file."""
        backup_file = tmp_path / "test_backup.json"
        with open(backup_file, "w") as f:
            json.dump(sample_backup_data, f)

        result = restore_manager.load_backup(backup_file)

        assert result == sample_backup_data

    def test_load_backup_file_not_found(self, restore_manager, tmp_path):
        """Test loading a non-existent backup file."""
        backup_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            restore_manager.load_backup(backup_file)

    def test_validate_backup_valid(self, restore_manager, sample_backup_data):
        """Test validating a valid backup."""
        # Should not raise any exception
        restore_manager.validate_backup(sample_backup_data)

    def test_validate_backup_missing_metadata(self, restore_manager):
        """Test validating backup with missing metadata."""
        invalid_backup = {
            "schema": {},
            "objects": []
        }

        with pytest.raises(ValueError, match="missing 'metadata' section"):
            restore_manager.validate_backup(invalid_backup)

    def test_validate_backup_missing_schema(self, restore_manager):
        """Test validating backup with missing schema."""
        invalid_backup = {
            "metadata": {"version": "1.0"},
            "objects": []
        }

        with pytest.raises(ValueError, match="missing 'schema' section"):
            restore_manager.validate_backup(invalid_backup)

    @patch('httpx.Client.get')
    def test_collection_exists_true(self, mock_get, restore_manager):
        """Test collection_exists returns True for existing collection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = restore_manager.collection_exists("TestCollection")

        assert result is True
        mock_get.assert_called_once_with("http://test-server:8080/v1/schema/TestCollection")

    @patch('httpx.Client.get')
    def test_collection_exists_false(self, mock_get, restore_manager):
        """Test collection_exists returns False for non-existent collection."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = restore_manager.collection_exists("NonExistentCollection")

        assert result is False

    def test_dry_run_restore(self, restore_manager, sample_backup_data):
        """Test dry run restore functionality."""
        with patch.object(restore_manager, 'collection_exists', return_value=False):
            result = restore_manager.dry_run_restore(sample_backup_data, "NewCollection", skip_data=False)

            assert result is True

    @patch('httpx.Client.post')
    def test_create_collection_from_schema(self, mock_post, restore_manager, sample_backup_data):
        """Test creating collection from schema."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        schema = sample_backup_data["schema"]
        restore_manager.create_collection_from_schema(schema, "NewCollection")

        # Verify the call was made with correct data
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test-server:8080/v1/schema"

        posted_data = call_args[1]["json"]
        assert posted_data["class"] == "NewCollection"
        assert posted_data["properties"] == schema["properties"]

    @patch('httpx.Client.post')
    def test_create_collection_from_schema_failure(self, mock_post, restore_manager, sample_backup_data):
        """Test creating collection from schema with failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        schema = sample_backup_data["schema"]

        with pytest.raises(Exception, match="Failed to create collection: Bad Request"):
            restore_manager.create_collection_from_schema(schema, "NewCollection")

    @patch('httpx.Client.post')
    def test_restore_object_batch(self, mock_post, restore_manager):
        """Test restoring a batch of objects."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        objects = [
            {
                "id": "test-id-1",
                "properties": {"content": "Test content"},
                "vector": [0.1, 0.2, 0.3]
            }
        ]

        restore_manager.restore_object_batch("TestCollection", objects)

        # Verify the batch endpoint was called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test-server:8080/v1/batch/objects"

        # Verify the batch endpoint was called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test-server:8080/v1/batch/objects"

        posted_data = call_args[1]["json"]
        assert "objects" in posted_data
        assert len(posted_data["objects"]) == 1
        assert posted_data["objects"][0]["class"] == "TestCollection"
        assert posted_data["objects"][0]["id"] == "test-id-1"


class TestEndToEndRestore:
    """End-to-end tests for complete backup/restore cycle."""

    @pytest.fixture
    def restore_manager(self):
        """Create RestoreManager instance for end-to-end tests."""
        return RestoreManager(base_url="http://test-server:8080")

    @pytest.fixture
    def sample_collection_data(self):
        """Create sample collection data for testing."""
        return {
            "class": "TestDocuments",
            "properties": [
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "Document title"
                },
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Document content"
                },
                {
                    "name": "category",
                    "dataType": ["string"],
                    "description": "Document category"
                }
            ],
            "replicationConfig": {"factor": 1},
            "shardingConfig": {"desiredCount": 1},
            "vectorizer": "text2vec-openai"
        }

    @pytest.fixture
    def sample_objects(self):
        """Create sample objects for testing."""
        return [
            {
                "id": "doc-001",
                "class": "TestDocuments",
                "properties": {
                    "title": "Introduction to AI",
                    "content": "This is an introduction to artificial intelligence...",
                    "category": "education"
                },
                "vector": [0.1, 0.2, 0.3, 0.4, 0.5]
            },
            {
                "id": "doc-002",
                "class": "TestDocuments",
                "properties": {
                    "title": "Machine Learning Basics",
                    "content": "Machine learning is a subset of AI...",
                    "category": "technology"
                },
                "vector": [0.6, 0.7, 0.8, 0.9, 1.0]
            },
            {
                "id": "doc-003",
                "class": "TestDocuments",
                "properties": {
                    "title": "Data Science Overview",
                    "content": "Data science combines statistics and programming...",
                    "category": "analytics"
                },
                "vector": [0.2, 0.4, 0.6, 0.8, 1.0]
            }
        ]

    @pytest.fixture
    def complete_backup_data(self, sample_collection_data, sample_objects):
        """Create complete backup data."""
        return {
            "metadata": {
                "version": "1.0",
                "timestamp": "2024-01-01T12:00:00Z",
                "collection": "TestDocuments",
                "weaviate_version": "1.23.0",
                "type": "full",
                "object_count": len(sample_objects)
            },
            "schema": sample_collection_data,
            "objects": sample_objects
        }

    def test_full_backup_restore_cycle(self, tmp_path, complete_backup_data):
        """Test complete backup to restore cycle with mocked services."""
        backup_file = tmp_path / "test_backup.json"

        # Save backup file
        with open(backup_file, "w") as f:
            json.dump(complete_backup_data, f)

        # Mock the RestoreManager's dependencies
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock collection existence check - collection doesn't exist
            mock_response_exists = Mock()
            mock_response_exists.status_code = 404
            mock_client.get.return_value = mock_response_exists

            # Mock schema creation
            mock_response_create = Mock()
            mock_response_create.status_code = 201
            mock_client.post.return_value = mock_response_create

            # Create RestoreManager and test restore
            restore_manager = RestoreManager()
            result = restore_manager.restore_collection(backup_file, "RestoredDocuments")

            # Verify the restore was successful
            assert result is True

            # Verify collection existence was checked
            mock_client.get.assert_called_with("http://localhost:8080/v1/schema/RestoredDocuments")

            # Verify schema was created with correct data
            schema_call = mock_client.post.call_args_list[0]
            assert schema_call[0][0] == "http://localhost:8080/v1/schema"
            posted_schema = schema_call[1]["json"]
            assert posted_schema["class"] == "RestoredDocuments"
            assert len(posted_schema["properties"]) == 3

            # Verify objects were restored
            batch_call = mock_client.post.call_args_list[1]
            assert batch_call[0][0] == "http://localhost:8080/v1/batch/objects"
            batch_data = batch_call[1]["json"]
            assert len(batch_data["objects"]) == 3
            assert batch_data["objects"][0]["class"] == "RestoredDocuments"

    def test_schema_only_restore(self, tmp_path, complete_backup_data):
        """Test schema-only restore (no data)."""
        # Modify backup to be schema-only
        schema_only_backup = complete_backup_data.copy()
        schema_only_backup["metadata"]["type"] = "schema-only"
        schema_only_backup["objects"] = []

        backup_file = tmp_path / "schema_backup.json"
        with open(backup_file, "w") as f:
            json.dump(schema_only_backup, f)

        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock responses
            mock_response_exists = Mock()
            mock_response_exists.status_code = 404
            mock_client.get.return_value = mock_response_exists

            mock_response_create = Mock()
            mock_response_create.status_code = 201
            mock_client.post.return_value = mock_response_create

            restore_manager = RestoreManager()
            result = restore_manager.restore_collection(backup_file, skip_data=True)

            assert result is True

            # Verify only schema creation call was made (no batch restore)
            assert mock_client.post.call_count == 1
            schema_call = mock_client.post.call_args
            assert schema_call[0][0] == "http://localhost:8080/v1/schema"

    def test_restore_with_custom_name(self, tmp_path, complete_backup_data):
        """Test restore with custom collection name."""
        backup_file = tmp_path / "test_backup.json"
        with open(backup_file, "w") as f:
            json.dump(complete_backup_data, f)

        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock responses
            mock_response_exists = Mock()
            mock_response_exists.status_code = 404
            mock_client.get.return_value = mock_response_exists

            mock_response_create = Mock()
            mock_response_create.status_code = 201
            mock_client.post.return_value = mock_response_create

            restore_manager = RestoreManager()
            result = restore_manager.restore_collection(backup_file, "MyCustomName")

            assert result is True

            # Verify schema was created with custom name
            schema_call = mock_client.post.call_args_list[0]
            posted_schema = schema_call[1]["json"]
            assert posted_schema["class"] == "MyCustomName"

            # Verify objects were restored to custom collection
            batch_call = mock_client.post.call_args_list[1]
            batch_data = batch_call[1]["json"]
            assert batch_call[0][0] == "http://localhost:8080/v1/batch/objects"
            assert batch_data["objects"][0]["class"] == "MyCustomName"

    def test_restore_existing_collection_fails(self, tmp_path, complete_backup_data):
        """Test that restore fails when target collection already exists."""
        backup_file = tmp_path / "test_backup.json"
        with open(backup_file, "w") as f:
            json.dump(complete_backup_data, f)

        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock collection already exists
            mock_response_exists = Mock()
            mock_response_exists.status_code = 200
            mock_client.get.return_value = mock_response_exists

            restore_manager = RestoreManager()
            result = restore_manager.restore_collection(backup_file, "ExistingCollection")

            # Should fail because collection exists
            assert result is False

            # Should not attempt to create schema or restore objects
            mock_client.post.assert_not_called()

    def test_dry_run_restore(self, tmp_path, complete_backup_data):
        """Test dry-run restore functionality."""
        backup_file = tmp_path / "test_backup.json"
        with open(backup_file, "w") as f:
            json.dump(complete_backup_data, f)

        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock collection doesn't exist
            mock_response_exists = Mock()
            mock_response_exists.status_code = 404
            mock_client.get.return_value = mock_response_exists

            restore_manager = RestoreManager()
            result = restore_manager.restore_collection(backup_file, "DryRunCollection", dry_run=True)

            assert result is True

            # Should not make any POST requests (no actual creation/restore)
            mock_client.post.assert_not_called()

            # Should only check if collection exists
            mock_client.get.assert_called_once_with("http://localhost:8080/v1/schema/DryRunCollection")

    def test_backup_validation_errors(self, tmp_path):
        """Test validation of invalid backup files."""
        # Test missing metadata
        invalid_backup = {"schema": {}, "objects": []}
        backup_file = tmp_path / "invalid_backup.json"
        with open(backup_file, "w") as f:
            json.dump(invalid_backup, f)

        restore_manager = RestoreManager()

        with pytest.raises(ValueError, match="missing 'metadata' section"):
            restore_manager.restore_collection(backup_file, dry_run=True)

        # Test missing schema
        invalid_backup2 = {"metadata": {"version": "1.0"}, "objects": []}
        with open(backup_file, "w") as f:
            json.dump(invalid_backup2, f)

        with pytest.raises(ValueError, match="missing 'schema' section"):
            restore_manager.restore_collection(backup_file, dry_run=True)

    def test_restore_file_not_found(self, restore_manager):
        """Test restore with non-existent backup file."""
        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            restore_manager.restore_collection(Path("/nonexistent/file.json"))

    def test_batch_restore_error_handling(self, tmp_path, complete_backup_data):
        """Test error handling during batch object restore."""
        backup_file = tmp_path / "test_backup.json"
        with open(backup_file, "w") as f:
            json.dump(complete_backup_data, f)

        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock successful collection check and schema creation
            mock_response_exists = Mock()
            mock_response_exists.status_code = 404
            mock_response_create = Mock()
            mock_response_create.status_code = 201

            # Mock batch restore failure
            mock_response_batch = Mock()
            mock_response_batch.status_code = 400
            mock_response_batch.raise_for_status.side_effect = Exception("Batch restore failed")

            # Configure different responses for different calls
            mock_client.get.return_value = mock_response_exists
            mock_client.post.side_effect = [mock_response_create, mock_response_batch]

            restore_manager = RestoreManager()

            with pytest.raises(Exception, match="Batch restore failed"):
                restore_manager.restore_collection(backup_file, "TestCollection")