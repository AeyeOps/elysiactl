"""Performance optimization for high-throughput sync operations."""

import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, AsyncIterator, Callable
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn

console = Console()

@dataclass
class PerformanceMetrics:
    """Track performance metrics during sync operations."""

    # Counters
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0

    # Timing
    start_time: float = 0.0
    end_time: Optional[float] = None

    # Throughput
    files_per_second: float = 0.0
    bytes_per_second: float = 0.0
    total_bytes: int = 0

    # Resource usage
    peak_memory_mb: float = 0.0
    active_connections: int = 0
    peak_connections: int = 0

    # Batching
    total_batches: int = 0
    avg_batch_size: float = 0.0
    avg_batch_time_ms: float = 0.0

    def start(self):
        """Start timing."""
        self.start_time = time.time()

    def finish(self):
        """Finish timing and calculate final metrics."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        if duration > 0:
            self.files_per_second = self.processed_files / duration
            self.bytes_per_second = self.total_bytes / duration

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        duration = (self.end_time or time.time()) - self.start_time

        return {
            'duration_seconds': duration,
            'files_per_second': self.files_per_second,
            'bytes_per_second': self.bytes_per_second,
            'throughput_mbps': self.bytes_per_second / (1024 * 1024),
            'total_files': self.total_files,
            'success_rate': self.successful_files / max(self.processed_files, 1) * 100,
            'peak_memory_mb': self.peak_memory_mb,
            'peak_connections': self.peak_connections,
            'avg_batch_size': self.avg_batch_size,
            'avg_batch_time_ms': self.avg_batch_time_ms
        }

class ConnectionPool:
    """Async HTTP connection pool with connection limits."""

    def __init__(self,
                 max_connections: int = 20,
                 max_connections_per_host: int = 10,
                 timeout: aiohttp.ClientTimeout = None):
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.timeout = timeout or aiohttp.ClientTimeout(total=30, connect=10)
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with optimized settings."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.max_connections,
                        limit_per_host=self.max_connections_per_host,
                        ttl_dns_cache=300,  # 5 minutes
                        use_dns_cache=True,
                        keepalive_timeout=60,
                        enable_cleanup_closed=True
                    )

                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=self.timeout,
                        headers={
                            'User-Agent': 'elysiactl/performance-optimized',
                            'Accept-Encoding': 'gzip, deflate'
                        }
                    )

        return self._session

    async def close(self):
        """Close connection pool."""
        if self._session and not self._session.closed:
            await self._session.close()

class BatchProcessor:
    """Efficient batch processing with parallel execution."""

    def __init__(self,
                 batch_size: int = 100,
                 max_workers: int = 4,
                 max_memory_mb: int = 512):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.max_memory_mb = max_memory_mb
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def process_batches(self,
                            items: AsyncIterator[Any],
                            processor: Callable,
                            progress: Optional[Progress] = None,
                            task: Optional[TaskID] = None) -> AsyncIterator[List[Any]]:
        """Process items in parallel batches."""
        batch = []

        async for item in items:
            batch.append(item)

            if len(batch) >= self.batch_size:
                # Process batch in parallel
                results = await self._process_batch_parallel(batch, processor)

                if progress and task:
                    progress.update(task, advance=len(batch))

                yield results
                batch.clear()

        # Process final partial batch
        if batch:
            results = await self._process_batch_parallel(batch, processor)

            if progress and task:
                progress.update(task, advance=len(batch))

            yield results

    async def _process_batch_parallel(self, batch: List[Any], processor: Callable) -> List[Any]:
        """Process a batch using parallel workers."""
        # Split batch into chunks for parallel processing
        chunk_size = max(1, len(batch) // self.max_workers)
        chunks = [batch[i:i + chunk_size] for i in range(0, len(batch), chunk_size)]

        # Process chunks in parallel
        tasks = []
        for chunk in chunks:
            task = asyncio.create_task(self._process_chunk(chunk, processor))
            tasks.append(task)

        # Wait for all chunks to complete
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        results = []
        for chunk_result in chunk_results:
            if isinstance(chunk_result, Exception):
                console.print(f"[red]Chunk processing error: {chunk_result}[/red]")
                continue
            results.extend(chunk_result)

        return results

    async def _process_chunk(self, chunk: List[Any], processor: Callable) -> List[Any]:
        """Process a chunk of items."""
        results = []
        for item in chunk:
            try:
                result = await processor(item)
                results.append(result)
            except Exception as e:
                console.print(f"[red]Item processing error: {e}[/red]")
                results.append(None)

        return results

    def shutdown(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=True)

class StreamingProcessor:
    """Streaming processor for large-scale operations."""

    def __init__(self,
                 buffer_size: int = 1000,
                 flush_interval: float = 5.0):
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.buffer: List[Any] = []
        self.buffer_lock = asyncio.Lock()
        self.last_flush_time = time.time()

    async def add_item(self, item: Any, processor: Callable) -> Optional[List[Any]]:
        """Add item to buffer, flush if needed."""
        async with self.buffer_lock:
            self.buffer.append(item)

            # Check if buffer should be flushed
            should_flush = (
                len(self.buffer) >= self.buffer_size or
                time.time() - self.last_flush_time >= self.flush_interval
            )

            if should_flush:
                return await self._flush_buffer(processor)

        return None

    async def flush(self, processor: Callable) -> List[Any]:
        """Force flush buffer."""
        async with self.buffer_lock:
            return await self._flush_buffer(processor)

    async def _flush_buffer(self, processor: Callable) -> List[Any]:
        """Internal buffer flush."""
        if not self.buffer:
            return []

        items = self.buffer.copy()
        self.buffer.clear()
        self.last_flush_time = time.time()

        # Process items
        results = []
        for item in items:
            try:
                result = await processor(item)
                results.append(result)
            except Exception as e:
                console.print(f"[red]Streaming processing error: {e}[/red]")
                results.append(None)

        return results

class PerformanceOptimizer:
    """Main performance optimization coordinator."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Performance settings
        self.max_workers = self.config.get('max_workers', 8)
        self.batch_size = self.config.get('batch_size', 100)
        self.max_connections = self.config.get('max_connections', 20)
        self.memory_limit_mb = self.config.get('memory_limit_mb', 512)

        # Components
        self.connection_pool = ConnectionPool(
            max_connections=self.max_connections,
            max_connections_per_host=self.max_connections // 2
        )
        self.batch_processor = BatchProcessor(
            batch_size=self.batch_size,
            max_workers=self.max_workers,
            max_memory_mb=self.memory_limit_mb
        )
        self.streaming_processor = StreamingProcessor(
            buffer_size=self.batch_size,
            flush_interval=2.0
        )

        # Metrics
        self.metrics = PerformanceMetrics()

    async def optimize_sync_operation(self,
                                    changes: AsyncIterator[Dict[str, Any]],
                                    processor: Callable) -> AsyncIterator[Dict[str, Any]]:
        """Optimize sync operation with parallel processing."""
        self.metrics.start()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[blue]{task.completed}/{task.total} files"),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task("Processing files...", total=None)

            # Process in optimized batches
            batch_count = 0
            async for batch_results in self.batch_processor.process_batches(
                changes, processor, progress, task
            ):
                batch_count += 1
                batch_size = len(batch_results)

                # Update metrics
                self.metrics.total_batches += 1
                self.metrics.processed_files += batch_size
                self.metrics.successful_files += sum(1 for r in batch_results if r and r.get('success', False))
                self.metrics.failed_files += sum(1 for r in batch_results if r and not r.get('success', True))

                # Calculate running averages
                self.metrics.avg_batch_size = self.metrics.processed_files / self.metrics.total_batches

                # Yield results
                for result in batch_results:
                    if result:
                        yield result

                # Memory management
                if batch_count % 10 == 0:  # Every 10 batches
                    await self._check_memory_usage()

        self.metrics.finish()

    async def _check_memory_usage(self):
        """Check and manage memory usage."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)

            self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, memory_mb)

            # If memory usage is high, trigger garbage collection
            if memory_mb > self.memory_limit_mb * 0.8:
                import gc
                gc.collect()

        except ImportError:
            pass  # psutil not available

    async def create_optimized_weaviate_client(self, base_url: str):
        """Create optimized Weaviate client with connection pooling."""
        session = await self.connection_pool.get_session()
        return OptimizedWeaviateClient(base_url, session, self.metrics)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = self.metrics.get_summary()

        # Add optimization details
        summary.update({
            'optimization_config': {
                'max_workers': self.max_workers,
                'batch_size': self.batch_size,
                'max_connections': self.max_connections,
                'memory_limit_mb': self.memory_limit_mb
            }
        })

        return summary

    async def cleanup(self):
        """Cleanup resources."""
        await self.connection_pool.close()
        self.batch_processor.shutdown()

class OptimizedWeaviateClient:
    """High-performance Weaviate client with batching and connection pooling."""

    def __init__(self, base_url: str, session: aiohttp.ClientSession, metrics: PerformanceMetrics):
        self.base_url = base_url.rstrip('/')
        self.session = session
        self.metrics = metrics
        self.batch_buffer: List[Dict[str, Any]] = []
        self.batch_lock = asyncio.Lock()

    async def batch_index_files(self,
                               operations: List[Dict[str, Any]],
                               collection: str) -> List[bool]:
        """Batch index multiple files for optimal performance."""
        if not operations:
            return []

        batch_start = time.time()

        # Prepare batch request
        batch_objects = []
        for op in operations:
            if op.get('operation') == 'delete':
                # Handle deletion
                continue

            batch_objects.append({
                "class": collection,
                "id": op.get('id'),
                "properties": op.get('properties', {}),
                "vector": op.get('vector')
            })

        try:
            # Send batch request
            url = f"{self.base_url}/batch/objects"

            async with self.session.put(url, json={"objects": batch_objects}) as response:
                self.metrics.active_connections += 1
                self.metrics.peak_connections = max(self.metrics.peak_connections, self.metrics.active_connections)

                if response.status == 200:
                    result = await response.json()
                    results = [True] * len(batch_objects)  # Simplified
                else:
                    console.print(f"[red]Batch request failed: {response.status}[/red]")
                    results = [False] * len(batch_objects)

                self.metrics.active_connections -= 1

        except Exception as e:
            console.print(f"[red]Batch index error: {e}[/red]")
            results = [False] * len(batch_objects)

        # Update metrics
        batch_time = (time.time() - batch_start) * 1000  # ms
        self.metrics.avg_batch_time_ms = (
            (self.metrics.avg_batch_time_ms * (self.metrics.total_batches - 1) + batch_time)
            / self.metrics.total_batches
        ) if self.metrics.total_batches > 0 else batch_time

        return results

# Global performance optimizer instance
_performance_optimizer: Optional[PerformanceOptimizer] = None

def get_performance_optimizer(config: Optional[Dict[str, Any]] = None) -> PerformanceOptimizer:
    """Get global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer(config)
    return _performance_optimizer