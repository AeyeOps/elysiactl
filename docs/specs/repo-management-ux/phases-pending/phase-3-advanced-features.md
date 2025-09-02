# Phase 3: Advanced Features Implementation

## Phase 3.1: Process & Quality Improvements (High Priority)

### Automated Integration Testing
- CI/CD pipeline for collection operations
- Automated end-to-end backup/restore testing
- Performance regression testing
- Multi-environment testing (dev/staging/prod)

### Configuration Management
- Move hardcoded values to configuration files
- Environment-specific settings
- Dynamic batch size calculation
- Configurable timeout and retry settings

### Monitoring & Observability
- Structured logging for operations
- Performance metrics collection
- Operation success/failure tracking
- Integration with monitoring systems

### Async Processing
- Background job processing for large operations
- Queue-based backup/restore operations
- Progress tracking and cancellation support
- Resource pool management

---

## Objective
Implement advanced collection management features including real-time statistics, cross-cluster operations, and performance optimization tools.

## Commands to Implement

### 1. Collection Statistics (`col stats`)

**File**: `/opt/elysiactl/src/elysiactl/commands/collection.py` (extend)

```python
@app.command("stats", help="Show collection statistics")
def collection_stats(
    name: str = typer.Argument(None, help="Collection name (all if not specified)"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Live update statistics"),
    interval: int = typer.Option(5, "--interval", help="Update interval in seconds"),
    format: str = typer.Option("table", "--format", help="Output format"),
    metrics: str = typer.Option("all", "--metrics", help="Metrics to display: all, basic, performance")
):
    """Display real-time statistics for collections."""
```

**Real-time Monitoring Implementation**:
```python
class CollectionMonitor:
    """Monitor collection statistics in real-time."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.Client()
        self.previous_stats = {}
    
    def get_collection_stats(self, collection_name: str) -> dict:
        """Get comprehensive statistics for a collection."""
        
        stats = {
            "name": collection_name,
            "timestamp": datetime.utcnow(),
            "objects": self.get_object_count(collection_name),
            "shards": self.get_shard_stats(collection_name),
            "performance": self.get_performance_metrics(collection_name),
            "storage": self.get_storage_info(collection_name),
            "vectors": self.get_vector_stats(collection_name)
        }
        
        # Calculate rates if we have previous data
        if collection_name in self.previous_stats:
            stats["rates"] = self.calculate_rates(
                self.previous_stats[collection_name],
                stats
            )
        
        self.previous_stats[collection_name] = stats
        return stats
    
    def get_shard_stats(self, collection_name: str) -> dict:
        """Get shard distribution statistics."""
        response = self.client.get(
            f"{self.base_url}/v1/schema/{collection_name}/shards"
        )
        response.raise_for_status()
        
        shards = response.json()
        return {
            "count": len(shards),
            "distribution": {
                shard["name"]: {
                    "objects": shard["objectCount"],
                    "status": shard["status"],
                    "vector_queue_length": shard.get("vectorQueueLength", 0)
                }
                for shard in shards
            }
        }
    
    def get_performance_metrics(self, collection_name: str) -> dict:
        """Get performance metrics for collection."""
        # Query latest metrics from Weaviate monitoring endpoint
        response = self.client.get(
            f"{self.base_url}/v1/metrics/collections/{collection_name}"
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "query_latency_ms": data.get("queryLatencyMs", 0),
                "import_rate": data.get("importRate", 0),
                "vector_index_operations": data.get("vectorIndexOps", 0),
                "cache_hit_rate": data.get("cacheHitRate", 0)
            }
        return {}
    
    def calculate_rates(self, previous: dict, current: dict) -> dict:
        """Calculate rate of change between measurements."""
        time_diff = (current["timestamp"] - previous["timestamp"]).total_seconds()
        
        if time_diff == 0:
            return {}
        
        object_diff = current["objects"] - previous["objects"]
        
        return {
            "objects_per_second": object_diff / time_diff,
            "growth_rate": (object_diff / previous["objects"] * 100) if previous["objects"] > 0 else 0
        }
    
    def watch_collections(self, collections: List[str], interval: int):
        """Watch collections and update display."""
        
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                try:
                    table = self.create_stats_table(collections)
                    live.update(table)
                    time.sleep(interval)
                except KeyboardInterrupt:
                    break
    
    def create_stats_table(self, collections: List[str]) -> Table:
        """Create a Rich table with current statistics."""
        
        table = Table(title=f"Collection Statistics - {datetime.now().strftime('%H:%M:%S')}")
        table.add_column("Collection", style="cyan")
        table.add_column("Objects", justify="right")
        table.add_column("Rate/s", justify="right")
        table.add_column("Shards", justify="right")
        table.add_column("Query ms", justify="right")
        table.add_column("Cache Hit", justify="right")
        
        for col_name in collections:
            stats = self.get_collection_stats(col_name)
            
            rate = stats.get("rates", {}).get("objects_per_second", 0)
            rate_str = f"+{rate:.1f}" if rate > 0 else f"{rate:.1f}" if rate < 0 else "0"
            
            table.add_row(
                col_name,
                f"{stats['objects']:,}",
                rate_str,
                str(stats["shards"]["count"]),
                f"{stats['performance'].get('query_latency_ms', 0):.1f}",
                f"{stats['performance'].get('cache_hit_rate', 0):.1%}"
            )
        
        return table
```

### 2. Collection Copy (`col copy`)

```python
@app.command("copy", help="Copy a collection")
def copy_collection(
    source: str = typer.Argument(..., help="Source collection name"),
    destination: str = typer.Argument(..., help="Destination collection name"),
    include_data: bool = typer.Option(True, "--include-data/--schema-only"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite if exists"),
    transform: Path = typer.Option(None, "--transform", help="Path to transformation script")
):
    """Copy collection with optional transformations."""
```

**Copy with Transformations**:
```python
class CollectionCopier:
    """Handle collection copying with transformations."""
    
    def copy_collection(
        self,
        source: str,
        destination: str,
        options: CopyOptions
    ) -> bool:
        """Copy collection with optional transformations."""
        
        # 1. Get source schema
        source_schema = self.get_schema(source)
        
        # 2. Apply schema transformations if specified
        if options.transform:
            dest_schema = self.apply_schema_transform(source_schema, options.transform)
        else:
            dest_schema = source_schema.copy()
        
        # 3. Update collection name
        dest_schema["class"] = destination
        
        # 4. Create destination collection
        if self.collection_exists(destination):
            if not options.overwrite:
                raise CollectionExistsError(f"Collection '{destination}' exists")
            self.delete_collection(destination)
        
        self.create_collection(dest_schema)
        
        # 5. Copy data if requested
        if options.include_data:
            self.copy_objects(source, destination, options.transform)
        
        return True
    
    def copy_objects(
        self,
        source: str,
        destination: str,
        transform_script: Path = None
    ):
        """Copy objects with optional transformation."""
        
        transformer = None
        if transform_script:
            transformer = self.load_transformer(transform_script)
        
        total = self.get_object_count(source)
        
        with show_progress(f"Copying {total:,} objects") as progress:
            task = progress.add_task("Copying...", total=total)
            
            for batch in self.fetch_batches(source):
                # Apply transformations if specified
                if transformer:
                    batch = [transformer(obj) for obj in batch]
                
                # Import to destination
                self.import_batch(destination, batch)
                progress.update(task, advance=len(batch))
    
    def load_transformer(self, script_path: Path):
        """Load transformation function from Python script."""
        
        spec = importlib.util.spec_from_file_location("transform", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, "transform"):
            raise ValueError("Transform script must define 'transform' function")
        
        return module.transform
```

**Example Transformation Script**:
```python
# transform_example.py
def transform(obj: dict) -> dict:
    """Transform object during copy."""
    
    # Add timestamp
    obj["properties"]["copied_at"] = datetime.utcnow().isoformat()
    
    # Rename field
    if "old_field" in obj["properties"]:
        obj["properties"]["new_field"] = obj["properties"].pop("old_field")
    
    # Filter sensitive data
    if "password" in obj["properties"]:
        del obj["properties"]["password"]
    
    return obj
```

### 3. Collection Migration (`col migrate`)

```python
@app.command("migrate", help="Migrate collection between clusters")
def migrate_collection(
    collection: str = typer.Argument(..., help="Collection to migrate"),
    target: str = typer.Option(..., "--target", help="Target cluster URL"),
    auth: str = typer.Option(None, "--auth", help="Authentication for target"),
    strategy: str = typer.Option("online", "--strategy", help="Migration strategy: online, offline"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify after migration")
):
    """Migrate collection to another Weaviate cluster."""
```

**Cross-Cluster Migration**:
```python
class CrossClusterMigrator:
    """Handle migration between Weaviate clusters."""
    
    def __init__(self, source_url: str, target_url: str):
        self.source = WeaviateClient(source_url)
        self.target = WeaviateClient(target_url)
        self.migration_id = str(uuid.uuid4())
    
    def migrate(
        self,
        collection_name: str,
        strategy: MigrationStrategy
    ) -> MigrationResult:
        """Perform cross-cluster migration."""
        
        if strategy == MigrationStrategy.ONLINE:
            return self.online_migration(collection_name)
        else:
            return self.offline_migration(collection_name)
    
    def online_migration(self, collection_name: str) -> MigrationResult:
        """Online migration with minimal downtime."""
        
        result = MigrationResult(
            migration_id=self.migration_id,
            start_time=datetime.utcnow()
        )
        
        try:
            # 1. Create collection on target
            schema = self.source.get_schema(collection_name)
            self.target.create_collection(schema)
            
            # 2. Initial bulk copy
            self.bulk_copy(collection_name)
            
            # 3. Track changes during migration
            change_tracker = ChangeTracker(self.source, collection_name)
            change_tracker.start()
            
            # 4. Sync remaining changes
            while change_tracker.has_changes():
                changes = change_tracker.get_changes()
                self.apply_changes(collection_name, changes)
            
            # 5. Final verification
            if self.verify_migration(collection_name):
                result.status = "SUCCESS"
            else:
                result.status = "VERIFICATION_FAILED"
            
        except Exception as e:
            result.status = "FAILED"
            result.error = str(e)
        
        result.end_time = datetime.utcnow()
        return result
    
    def verify_migration(self, collection_name: str) -> bool:
        """Verify data integrity after migration."""
        
        source_count = self.source.get_object_count(collection_name)
        target_count = self.target.get_object_count(collection_name)
        
        if source_count != target_count:
            console.print(f"[red]Count mismatch: source={source_count}, target={target_count}[/red]")
            return False
        
        # Sample verification
        sample_size = min(100, source_count // 10)
        source_sample = self.source.get_random_objects(collection_name, sample_size)
        
        for obj in source_sample:
            target_obj = self.target.get_object(collection_name, obj["id"])
            if not self.objects_equal(obj, target_obj):
                console.print(f"[red]Object mismatch: {obj['id']}[/red]")
                return False
        
        return True
```

### 4. Collection Optimization (`col optimize`)

```python
@app.command("optimize", help="Optimize collection performance")
def optimize_collection(
    name: str = typer.Argument(..., help="Collection name"),
    operation: str = typer.Option("auto", "--operation", help="Optimization: auto, reindex, compact, rebalance"),
    analyze: bool = typer.Option(True, "--analyze", help="Analyze before optimizing"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show optimization plan without executing")
):
    """Optimize collection for better performance."""
```

**Optimization Engine**:
```python
class CollectionOptimizer:
    """Optimize collection performance."""
    
    def analyze_collection(self, collection_name: str) -> OptimizationPlan:
        """Analyze collection and suggest optimizations."""
        
        analysis = {
            "fragmentation": self.check_fragmentation(collection_name),
            "shard_balance": self.check_shard_balance(collection_name),
            "index_efficiency": self.check_index_efficiency(collection_name),
            "vector_dimensions": self.check_vector_optimization(collection_name)
        }
        
        plan = OptimizationPlan()
        
        # Fragmentation optimization
        if analysis["fragmentation"]["level"] > 0.3:
            plan.add_action("compact", priority=1)
        
        # Shard rebalancing
        if analysis["shard_balance"]["imbalance_ratio"] > 0.2:
            plan.add_action("rebalance", priority=2)
        
        # Index optimization
        if analysis["index_efficiency"]["cache_misses"] > 0.5:
            plan.add_action("reindex", priority=3)
        
        return plan
    
    def compact_collection(self, collection_name: str):
        """Compact collection to reduce fragmentation."""
        
        console.print(f"[yellow]Compacting {collection_name}...[/yellow]")
        
        # Trigger Weaviate compaction
        response = self.client.post(
            f"{self.base_url}/v1/schema/{collection_name}/maintenance/compact"
        )
        response.raise_for_status()
        
        # Monitor compaction progress
        self.monitor_operation("compaction", collection_name)
    
    def rebalance_shards(self, collection_name: str):
        """Rebalance shards across nodes."""
        
        shards = self.get_shard_distribution(collection_name)
        optimal_distribution = self.calculate_optimal_distribution(shards)
        
        for shard_id, target_node in optimal_distribution.items():
            self.move_shard(collection_name, shard_id, target_node)
    
    def reindex_collection(self, collection_name: str):
        """Rebuild collection indexes for better performance."""
        
        console.print(f"[yellow]Reindexing {collection_name}...[/yellow]")
        
        # Trigger reindexing
        response = self.client.post(
            f"{self.base_url}/v1/schema/{collection_name}/maintenance/reindex",
            json={"vector_index": True, "inverted_index": True}
        )
        response.raise_for_status()
        
        self.monitor_operation("reindexing", collection_name)
```

### 5. Collection Health Check (`col health`)

```python
@app.command("health", help="Check collection health")
def collection_health(
    name: str = typer.Argument(None, help="Collection name (all if not specified)"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed diagnostics"),
    fix: bool = typer.Option(False, "--fix", help="Attempt to fix issues")
):
    """Perform health checks on collections."""
```

**Health Check System**:
```python
class CollectionHealthChecker:
    """Check and diagnose collection health issues."""
    
    def check_health(self, collection_name: str) -> HealthReport:
        """Comprehensive health check for collection."""
        
        report = HealthReport(collection_name)
        
        # Check availability
        report.add_check("availability", self.check_availability(collection_name))
        
        # Check replication
        report.add_check("replication", self.check_replication_health(collection_name))
        
        # Check data integrity
        report.add_check("integrity", self.check_data_integrity(collection_name))
        
        # Check performance
        report.add_check("performance", self.check_performance_health(collection_name))
        
        # Check resource usage
        report.add_check("resources", self.check_resource_usage(collection_name))
        
        return report
    
    def check_replication_health(self, collection_name: str) -> CheckResult:
        """Check replication status across nodes."""
        
        result = CheckResult("replication")
        
        shards = self.get_shard_status(collection_name)
        unhealthy_shards = [s for s in shards if s["status"] != "READY"]
        
        if unhealthy_shards:
            result.status = "WARNING"
            result.message = f"{len(unhealthy_shards)} shards not ready"
            result.details = unhealthy_shards
        else:
            result.status = "HEALTHY"
            result.message = "All shards properly replicated"
        
        return result
    
    def auto_fix_issues(self, collection_name: str, report: HealthReport):
        """Attempt to automatically fix detected issues."""
        
        fixes_applied = []
        
        for check_name, result in report.checks.items():
            if result.status in ["ERROR", "WARNING"]:
                fix_method = getattr(self, f"fix_{check_name}", None)
                if fix_method:
                    try:
                        fix_method(collection_name, result)
                        fixes_applied.append(check_name)
                    except Exception as e:
                        console.print(f"[red]Failed to fix {check_name}: {e}[/red]")
        
        return fixes_applied
```

## Advanced Features

### Batch Operations
```python
@app.command("batch", help="Perform batch operations on multiple collections")
def batch_operations(
    pattern: str = typer.Option("*", "--pattern", help="Collection name pattern"),
    operation: str = typer.Option(..., "--operation", help="Operation: backup, optimize, health"),
    parallel: int = typer.Option(1, "--parallel", help="Number of parallel operations")
):
    """Execute operations on multiple collections."""
    
    collections = get_collections_by_pattern(pattern)
    
    if parallel > 1:
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = []
            for col in collections:
                future = executor.submit(execute_operation, col, operation)
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                console.print(f"✓ {result}")
    else:
        for col in collections:
            execute_operation(col, operation)
```

### Collection Templates
```python
class CollectionTemplateManager:
    """Manage reusable collection templates."""
    
    def __init__(self):
        self.template_dir = Path.home() / ".elysiactl" / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)
    
    def save_template(self, name: str, schema: dict):
        """Save collection schema as template."""
        template_file = self.template_dir / f"{name}.json"
        
        # Remove instance-specific data
        template = self.clean_schema_for_template(schema)
        
        with open(template_file, "w") as f:
            json.dump(template, f, indent=2)
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        return [f.stem for f in self.template_dir.glob("*.json")]
    
    def load_template(self, name: str) -> dict:
        """Load template schema."""
        template_file = self.template_dir / f"{name}.json"
        
        if not template_file.exists():
            raise TemplateNotFoundError(f"Template '{name}' not found")
        
        with open(template_file) as f:
            return json.load(f)
    
    def create_from_template(
        self,
        template_name: str,
        collection_name: str,
        modifications: dict = None
    ):
        """Create collection from template with modifications."""
        
        schema = self.load_template(template_name)
        schema["class"] = collection_name
        
        if modifications:
            schema = self.apply_modifications(schema, modifications)
        
        return create_collection(schema)
```

## Performance Monitoring Dashboard

```python
class CollectionDashboard:
    """Terminal dashboard for collection monitoring."""
    
    def __init__(self):
        self.layout = self.create_layout()
    
    def create_layout(self) -> Layout:
        """Create Rich layout for dashboard."""
        
        return Layout(
            name="root",
            renderable=Layout(name="header", size=3),
            Layout(
                Layout(name="stats", ratio=2),
                Layout(name="logs", ratio=1),
                direction="horizontal"
            )
        )
    
    def run(self, collections: List[str]):
        """Run the dashboard."""
        
        with Live(self.layout, refresh_per_second=1) as live:
            while True:
                try:
                    self.update_header()
                    self.update_stats(collections)
                    self.update_logs()
                    time.sleep(1)
                except KeyboardInterrupt:
                    break
    
    def update_stats(self, collections: List[str]):
        """Update statistics panel."""
        
        stats_table = Table(show_header=True, header_style="bold magenta")
        stats_table.add_column("Collection")
        stats_table.add_column("Objects", justify="right")
        stats_table.add_column("QPS", justify="right")
        stats_table.add_column("Latency", justify="right")
        stats_table.add_column("Health")
        
        for col in collections:
            stats = get_collection_stats(col)
            health_color = "green" if stats["health"] == "HEALTHY" else "red"
            
            stats_table.add_row(
                col,
                f"{stats['objects']:,}",
                f"{stats['qps']:.1f}",
                f"{stats['latency']:.1f}ms",
                f"[{health_color}]{stats['health']}[/{health_color}]"
            )
        
        self.layout["stats"].update(Panel(stats_table, title="Collection Statistics"))
```

## Testing Strategy

### Performance Tests
```python
# tests/performance/test_large_collections.py

def test_stats_performance_large_collection():
    """Test statistics gathering on large collections."""
    
    # Create collection with 1M objects
    create_large_test_collection("PerfTest", 1_000_000)
    
    start = time.time()
    stats = get_collection_stats("PerfTest")
    duration = time.time() - start
    
    assert duration < 2.0  # Should complete within 2 seconds
    assert stats["objects"] == 1_000_000

def test_migration_performance():
    """Test migration speed between clusters."""
    
    # Setup source and target clusters
    source = setup_test_cluster(port=8080)
    target = setup_test_cluster(port=8081)
    
    # Create and populate collection
    create_test_collection("MigrationTest", 10_000)
    
    # Measure migration time
    start = time.time()
    migrate_collection("MigrationTest", target_url="http://localhost:8081")
    duration = time.time() - start
    
    # Should migrate at least 1000 objects/second
    assert duration < 10.0
```

## Success Metrics

1. **Performance**
   - Stats refresh < 500ms
   - Migration speed > 1000 objects/second
   - Optimization analysis < 5 seconds

2. **Reliability**
   - Zero data loss during migrations
   - Accurate health diagnostics
   - Successful auto-fix rate > 80%

3. **Usability**
   - Intuitive dashboard interface
   - Clear optimization recommendations
   - Helpful error recovery suggestions