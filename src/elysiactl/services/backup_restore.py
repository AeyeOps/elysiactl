"""Backup and restore functionality for elysiactl."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn

console = Console()


class BackupManager:
    """Handle collection backup operations."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def backup_schema_only(self, collection_name: str, output_dir: Path, dry_run: bool = False) -> Optional[Path]:
        """Create schema-only backup of a collection."""

        # Validate collection exists
        if not self.collection_exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' not found")

        if dry_run:
            return self._dry_run_backup(collection_name, output_dir)

        # Get schema
        schema = self.get_collection_schema(collection_name)
        object_count = self.get_object_count(collection_name)

        # Create backup metadata
        backup_meta = {
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collection": collection_name,
            "weaviate_version": self.get_weaviate_version(),
            "type": "schema-only",
            "object_count": object_count
        }

        # Create backup structure
        backup_data = {
            "metadata": backup_meta,
            "schema": schema,
            "objects": []
        }

        # Save backup
        return self.save_backup(backup_data, output_dir, collection_name, include_data=False)

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            response = self.client.get(f"{self.base_url}/v1/schema/{collection_name}")
            return response.status_code == 200
        except:
            return False

    def get_collection_schema(self, collection_name: str) -> dict:
        """Get collection schema."""
        response = self.client.get(f"{self.base_url}/v1/schema/{collection_name}")
        response.raise_for_status()
        return response.json()

    def get_object_count(self, collection_name: str) -> int:
        """Get object count for collection."""
        try:
            response = self.client.get(
                f"{self.base_url}/v1/objects",
                params={"class": collection_name, "limit": 0}
            )
            response.raise_for_status()
            return response.json().get("totalResults", 0)
        except:
            return 0

    def get_weaviate_version(self) -> str:
        """Get Weaviate version."""
        try:
            response = self.client.get(f"{self.base_url}/v1/meta")
            response.raise_for_status()
            return response.json().get("version", "unknown")
        except:
            return "unknown"

    def save_backup(self, backup_data: dict, output_dir: Path, collection_name: str, include_data: bool = False) -> Path:
        """Save backup to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_type = "full" if include_data else "schema"
        filename = f"{collection_name}_{backup_type}_{timestamp}.json"
        backup_path = output_dir / filename

        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)

        file_size = backup_path.stat().st_size
        console.print(f"[green]✓ {backup_type.title()} backup saved: {backup_path} ({file_size:,} bytes)[/green]")

        return backup_path

    def _dry_run_backup(self, collection_name: str, output_dir: Path) -> None:
        """Show what would be backed up without creating files."""
        console.print(f"[yellow]DRY RUN: Schema backup of '{collection_name}'[/yellow]")
        console.print(f"Output directory: {output_dir}")

        if self.collection_exists(collection_name):
            schema = self.get_collection_schema(collection_name)
            obj_count = self.get_object_count(collection_name)

            console.print(f"[green]✓ Collection exists: {collection_name}[/green]")
            console.print(f"  Object count: {obj_count}")
            console.print(f"  Properties: {len(schema.get('properties', []))}")
            console.print(f"  Replication factor: {schema.get('replicationConfig', {}).get('factor', 1)}")
        else:
            console.print(f"[red]✗ Collection not found: {collection_name}[/red]")

        return None

    def backup_with_data(self, collection_name: str, output_dir: Path, dry_run: bool = False, include_vectors: bool = False) -> Optional[Path]:
        """Create full backup of a collection including data.

        Args:
            collection_name: Name of collection to backup
            output_dir: Directory to save backup file
            dry_run: If True, show what would be backed up without creating files
            include_vectors: If True, include vector embeddings (can be very large)
        """
        # Validate collection exists
        if not self.collection_exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' not found")

        if dry_run:
            return self._dry_run_backup_with_data(collection_name, output_dir, include_vectors)

        # Get schema and object count
        schema = self.get_collection_schema(collection_name)
        object_count = self.get_object_count(collection_name)

        if object_count == 0:
            console.print(f"[yellow]Collection '{collection_name}' is empty, creating schema-only backup[/yellow]")
            return self.backup_schema_only(collection_name, output_dir, dry_run=False)

        console.print(f"[bold]Backing up collection '{collection_name}' with {object_count:,} objects[/bold]")
        if not include_vectors:
            console.print(f"[dim]Note: Vector embeddings will be excluded to reduce backup size[/dim]")

        # Estimate backup size
        estimated_size = self._estimate_backup_size(object_count, schema, include_vectors)
        console.print(f"[dim]Estimated backup size: ~{estimated_size:,} bytes[/dim]")

        # Fetch all objects with progress and memory management
        objects = self._fetch_all_objects_streaming(collection_name, object_count, include_vectors)

        # Create backup metadata
        backup_meta = {
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collection": collection_name,
            "weaviate_version": self.get_weaviate_version(),
            "type": "full-backup",
            "object_count": len(objects),
            "include_vectors": include_vectors,
            "estimated_size_bytes": estimated_size
        }

        # Create backup structure
        backup_data = {
            "metadata": backup_meta,
            "schema": schema,
            "objects": objects
        }

        # Save backup with streaming for large files
        return self.save_backup_streaming(backup_data, output_dir, collection_name, include_data=True)

    def _estimate_backup_size(self, object_count: int, schema: dict, include_vectors: bool) -> int:
        """Estimate backup file size in bytes."""
        # Rough estimates per object
        base_per_object = 200  # JSON overhead, metadata
        per_property = 50      # Average property size

        properties = schema.get("properties", [])
        property_overhead = len(properties) * per_property

        # Vector overhead (if included) - assume 768 dimensions for typical embeddings
        vector_overhead = 768 * 4 * 2 if include_vectors else 0  # 4 bytes per float, *2 for JSON

        per_object_total = base_per_object + property_overhead + vector_overhead

        # Add schema size (one-time)
        schema_size = len(json.dumps(schema))

        # Add metadata size
        metadata_size = 1000

        total_estimated = (object_count * per_object_total) + schema_size + metadata_size

        return total_estimated

    def _fetch_all_objects_streaming(self, collection_name: str, total_objects: int, include_vectors: bool) -> List[Dict[str, Any]]:
        """Fetch all objects with memory-efficient streaming and retry logic."""
        objects = []
        batch_size = 100  # Smaller batches for memory management
        offset = 0
        max_retries = 3
        retry_delay = 1.0

        with Progress() as progress:
            task = progress.add_task(f"Fetching objects from {collection_name}...", total=total_objects)

            while len(objects) < total_objects:
                batch_objects = []
                retry_count = 0

                while retry_count < max_retries:
                    try:
                        # Build request parameters
                        params = {
                            "class": collection_name,
                            "limit": batch_size,
                            "offset": offset
                        }

                        # Exclude vectors unless explicitly requested
                        if not include_vectors:
                            params["include"] = "properties"

                        # Fetch batch
                        response = self.client.get(
                            f"{self.base_url}/v1/objects",
                            params=params,
                            timeout=60.0  # Longer timeout for large batches
                        )
                        response.raise_for_status()
                        data = response.json()

                        batch_objects = data.get("objects", [])

                        # Remove vector data if not requested (extra safety)
                        if not include_vectors:
                            for obj in batch_objects:
                                if "vector" in obj:
                                    del obj["vector"]

                        break  # Success, exit retry loop

                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            console.print(f"[red]Failed to fetch batch at offset {offset} after {max_retries} retries: {e}[/red]")
                            raise

                        console.print(f"[yellow]Retry {retry_count}/{max_retries} for batch at offset {offset}: {e}[/yellow]")
                        import time
                        time.sleep(retry_delay * retry_count)  # Exponential backoff

                # Add batch to results
                objects.extend(batch_objects)

                # Update progress
                progress.update(task, completed=len(objects))

                # Check if we got fewer objects than requested (end of data)
                if len(batch_objects) < batch_size:
                    break

                offset += batch_size

                # Memory management: yield control periodically
                if len(objects) % 1000 == 0:
                    import time
                    time.sleep(0.01)  # Small yield to prevent blocking

        return objects

    def save_backup_streaming(self, backup_data: dict, output_dir: Path, collection_name: str, include_data: bool = False) -> Path:
        """Save backup to JSON file with streaming for large datasets."""
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_type = "full" if include_data else "schema"
        filename = f"{collection_name}_{backup_type}_{timestamp}.json"
        backup_path = output_dir / filename

        # For large datasets, use streaming JSON writing
        object_count = len(backup_data.get("objects", []))
        if object_count > 10000:  # Threshold for streaming
            self._save_large_backup(backup_path, backup_data)
        else:
            with open(backup_path, "w") as f:
                json.dump(backup_data, f, indent=2)

        file_size = backup_path.stat().st_size
        console.print(f"[green]✓ {backup_type.title()} backup saved: {backup_path} ({file_size:,} bytes)[/green]")

        return backup_path

    def _save_large_backup(self, backup_path: Path, backup_data: dict) -> None:
        """Save large backup files with streaming to manage memory."""
        with open(backup_path, "w") as f:
            # Write opening
            f.write("{\n")

            # Write metadata
            f.write('  "metadata": ')
            json.dump(backup_data["metadata"], f, indent=2)
            f.write(",\n")

            # Write schema
            f.write('  "schema": ')
            json.dump(backup_data["schema"], f, indent=2)
            f.write(",\n")

            # Write objects array
            f.write('  "objects": [\n')

            objects = backup_data["objects"]
            for i, obj in enumerate(objects):
                # Write object
                f.write("    ")
                json.dump(obj, f, indent=4)
                if i < len(objects) - 1:
                    f.write(",")
                f.write("\n")

                # Yield control periodically for large files
                if i % 1000 == 0:
                    f.flush()

            f.write("  ]\n")
            f.write("}\n")

    def _dry_run_backup_with_data(self, collection_name: str, output_dir: Path, include_vectors: bool = False) -> None:
        """Show what would be backed up including data without creating files."""
        console.print(f"[yellow]DRY RUN: Full backup of '{collection_name}'[/yellow]")
        console.print(f"Output directory: {output_dir}")

        if self.collection_exists(collection_name):
            schema = self.get_collection_schema(collection_name)
            obj_count = self.get_object_count(collection_name)

            console.print(f"[green]✓ Collection exists: {collection_name}[/green]")
            console.print(f"  Object count: {obj_count:,}")
            console.print(f"  Properties: {len(schema.get('properties', []))}")
            console.print(f"  Replication factor: {schema.get('replicationConfig', {}).get('factor', 1)}")

            # Size estimation
            estimated_size = self._estimate_backup_size(obj_count, schema, include_vectors)
            console.print(f"  Estimated backup size: ~{estimated_size:,} bytes")

            if include_vectors:
                console.print(f"[red]⚠ WARNING: Including vector embeddings will significantly increase backup size[/red]")
            else:
                console.print(f"[blue]ℹ Vector embeddings will be excluded (use --include-vectors to include them)[/blue]")

            console.print(f"[blue]  This will include all {obj_count:,} objects in the backup[/blue]")
        else:
            console.print(f"[red]✗ Collection not found: {collection_name}[/red]")

        return None


class RestoreManager:
    """Handle collection restore operations."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def restore_collection(self, backup_path: Path, collection_name: str = None, skip_data: bool = False, dry_run: bool = False) -> bool:
        """Restore a collection from backup."""

        # 1. Load and validate backup
        backup_data = self.load_backup(backup_path)
        self.validate_backup(backup_data)

        # 2. Determine target collection name
        target_name = collection_name or backup_data["schema"]["class"]

        if dry_run:
            return self.dry_run_restore(backup_data, target_name, skip_data)

        # 3. Check if collection already exists
        if self.collection_exists(target_name):
            console.print(f"[red]✗ Collection '{target_name}' already exists[/red]")
            console.print("[yellow]Use --merge option when implemented (Phase 2D)[/yellow]")
            return False

        # 4. Create collection with schema
        console.print(f"[bold]Creating collection '{target_name}'...[/bold]")
        self.create_collection_from_schema(backup_data["schema"], target_name)

        # 5. Restore data if requested and available
        if not skip_data and backup_data.get("objects"):
            self.restore_objects_with_progress(target_name, backup_data["objects"])

        console.print(f"[green]✓ Collection '{target_name}' restored successfully[/green]")
        return True

    def load_backup(self, backup_path: Path) -> dict:
        """Load backup file."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        with open(backup_path, "r") as f:
            return json.load(f)

    def validate_backup(self, backup_data: dict):
        """Validate backup file structure."""
        required_keys = ["metadata", "schema"]

        for key in required_keys:
            if key not in backup_data:
                raise ValueError(f"Invalid backup file: missing '{key}' section")

        # Validate metadata
        meta = backup_data["metadata"]
        if meta.get("version") != "1.0":
            console.print(f"[yellow]⚠ Backup version {meta.get('version')} may not be fully compatible[/yellow]")

    def create_collection_from_schema(self, schema: dict, collection_name: str):
        """Create collection using schema from backup."""

        # Update schema with new collection name
        create_schema = schema.copy()
        create_schema["class"] = collection_name

        response = self.client.post(
            f"{self.base_url}/v1/schema",
            json=create_schema
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create collection: {response.text}")

    def restore_objects_with_progress(self, collection_name: str, objects: List[dict]):
        """Restore objects with progress tracking."""

        total_objects = len(objects)
        console.print(f"[bold]Restoring {total_objects:,} objects...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:

            task = progress.add_task("Restoring objects", total=total_objects)

            # Process in batches for performance
            batch_size = 100
            for i in range(0, total_objects, batch_size):
                batch = objects[i:i + batch_size]
                self.restore_object_batch(collection_name, batch)
                progress.update(task, advance=len(batch))

    def restore_object_batch(self, collection_name: str, objects: List[dict]):
        """Restore a batch of objects."""

        # Prepare batch for Weaviate
        batch_objects = []
        for obj in objects:
            batch_objects.append({
                "class": collection_name,
                "id": obj.get("id"),
                "properties": obj.get("properties", {}),
                "vector": obj.get("vector")
            })

        batch_payload = {"objects": batch_objects}

        response = self.client.post(
            f"{self.base_url}/v1/batch/objects",
            json=batch_payload
        )

        response.raise_for_status()

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            response = self.client.get(f"{self.base_url}/v1/schema/{collection_name}")
            return response.status_code == 200
        except:
            return False

    def dry_run_restore(self, backup_data: dict, collection_name: str, skip_data: bool) -> bool:
        """Show what would be restored without making changes."""

        console.print(f"[bold]Dry Run: Restore to '{collection_name}'[/bold]")

        meta = backup_data["metadata"]
        schema = backup_data["schema"]

        console.print(f"Backup version: {meta.get('version')}")
        console.print(f"Original collection: {meta.get('collection')}")
        console.print(f"Object count: {meta.get('object_count', 0)}")
        console.print(f"Target collection: {collection_name}")

        # Check if target collection exists
        if self.collection_exists(collection_name):
            console.print(f"[yellow]⚠ Target collection '{collection_name}' already exists[/yellow]")
        else:
            console.print(f"[green]✓ Target collection '{collection_name}' available[/green]")

        # Show schema info
        properties = schema.get("properties", [])
        console.print(f"Schema properties: {len(properties)}")
        for prop in properties[:5]:  # Show first 5
            console.print(f"  - {prop['name']}: {prop['dataType']}")

        if len(properties) > 5:
            console.print(f"  ... and {len(properties) - 5} more")

        if not skip_data and backup_data.get("objects"):
            console.print(f"Objects to restore: {len(backup_data['objects'])}")

        return True