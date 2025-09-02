"""Performance benchmark tests for sync operations."""

import pytest
from pathlib import Path
from typing import List, Dict, Any
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_performance_optimizer_initialization(self):
        """Test that performance optimizer initializes correctly."""
        from elysiactl.services.performance import PerformanceOptimizer
        
        config = {
            'max_workers': 4,
            'batch_size': 50,
            'max_connections': 10,
            'memory_limit_mb': 256
        }
        
        optimizer = PerformanceOptimizer(config)
        
        # Test configuration is applied
        assert optimizer.max_workers == 4
        assert optimizer.batch_size == 50
        assert optimizer.max_connections == 10
        assert optimizer.memory_limit_mb == 256
        
        # Test components are initialized
        assert optimizer.connection_pool is not None
        assert optimizer.batch_processor is not None
        assert optimizer.streaming_processor is not None
        assert optimizer.metrics is not None
        
        # Test performance summary
        summary = optimizer.get_performance_summary()
        assert 'optimization_config' in summary
        assert summary['optimization_config']['max_workers'] == 4
    
    def test_batch_processor_configuration(self):
        """Test batch processor configuration."""
        from elysiactl.services.performance import BatchProcessor
        
        processor = BatchProcessor(batch_size=25, max_workers=3, max_memory_mb=128)
        
        assert processor.batch_size == 25
        assert processor.max_workers == 3
        assert processor.max_memory_mb == 128
        assert processor.executor is not None
        
        processor.shutdown()
    
    def test_connection_pool_configuration(self):
        """Test connection pool configuration."""
        from elysiactl.services.performance import ConnectionPool
        import aiohttp
        
        pool = ConnectionPool(max_connections=5, max_connections_per_host=3)
        
        assert pool.max_connections == 5
        assert pool.max_connections_per_host == 3
        assert isinstance(pool.timeout, aiohttp.ClientTimeout)
    
    def test_performance_metrics_tracking(self):
        """Test performance metrics tracking."""
        from elysiactl.services.performance import PerformanceMetrics
        
        metrics = PerformanceMetrics()
        
        # Test initial state
        assert metrics.total_files == 0
        assert metrics.processed_files == 0
        assert metrics.successful_files == 0
        assert metrics.failed_files == 0
        assert metrics.files_per_second == 0.0
        
        # Test starting timing
        metrics.start()
        assert metrics.start_time > 0
        
        # Test updating counters
        metrics.total_files = 100
        metrics.processed_files = 95
        metrics.successful_files = 90
        metrics.failed_files = 5
        metrics.total_bytes = 1024000  # 1MB
        
        # Test finishing timing
        metrics.finish()
        assert metrics.end_time > 0
        assert metrics.files_per_second > 0
        assert metrics.bytes_per_second > 0
        
        # Test summary generation
        summary = metrics.get_summary()
        assert 'duration_seconds' in summary
        assert 'files_per_second' in summary
        assert 'bytes_per_second' in summary
        assert 'throughput_mbps' in summary
        assert 'success_rate' in summary
        assert abs(summary['success_rate'] - 94.73684210526316) < 0.0001  # Allow small floating point difference

# Benchmark runner
def run_performance_benchmarks():
    """Run performance benchmark suite."""
    pytest_args = [
        str(Path(__file__)),
        "-v",
        "-m", "benchmark",
        "--durations=10",
        "--tb=short"
    ]
    
    return pytest.main(pytest_args)

if __name__ == "__main__":
    exit_code = run_performance_benchmarks()
    sys.exit(exit_code)
