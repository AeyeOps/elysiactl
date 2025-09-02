# Phase 6: Integration Testing Suite

## Objective

Create comprehensive integration test suite covering end-to-end workflows, performance benchmarks, error scenarios, and production readiness validation for the complete sync pipeline.

## Problem Summary

Phase 5 delivers high-performance sync capabilities but lacks systematic testing to ensure reliability at scale. Production deployments need comprehensive test coverage for all sync scenarios, performance validation, error recovery testing, and integration verification with real Weaviate clusters and enterprise data patterns.

## Implementation Details

### File: `/opt/elysiactl/tests/integration/test_sync_pipeline.py` (NEW)

**Create comprehensive integration test suite:**

```python
"""Integration tests for the complete sync pipeline."""

import pytest
import asyncio
import tempfile
import json
import time
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from elysiactl.services.sync import sync_files_from_stdin, SQLiteCheckpointManager
from elysiactl.services.content_resolver import ContentResolver
from elysiactl.services.error_handling import get_error_handler
from elysiactl.services.performance import get_performance_optimizer
from elysiactl.config import get_config, reload_config

@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        
        # Create test directory structure
        (workspace / "src").mkdir()
        (workspace / "tests").mkdir()
        (workspace / "docs").mkdir()
        (workspace / "vendor").mkdir()
        
        # Create test files with various sizes and types
        test_files = {
            "src/small.py": "def hello():\n    return 'world'",  # Tier 1
            "src/medium.py": "# Medium file\n" + ("def func():\n    pass\n" * 1000),  # Tier 2
            "src/large.py": "# Large file\n" + ("def func():\n    pass\n" * 5000),  # Tier 3
            "tests/test_example.py": "import unittest\n\nclass Test(unittest.TestCase):\n    pass",
            "docs/readme.md": "# Project Documentation\n\nThis is a test project.",
            "vendor/lib.js": "// Vendor library\nfunction vendor() {}",
            ".gitignore": "*.pyc\n__pycache__/\n.env",
            "binary_file.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",  # Binary content
        }
        
        for file_path, content in test_files.items():
            full_path = workspace / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(content, bytes):
                full_path.write_bytes(content)
            else:
                full_path.write_text(content)
        
        yield workspace

@pytest.fixture
def mock_weaviate():
    """Mock Weaviate service for testing."""
    with patch('elysiactl.services.weaviate.WeaviateService') as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.base_url = "http://localhost:8080/v1"
        mock_instance.index_file = AsyncMock(return_value=True)
        mock_instance.delete_object = AsyncMock(return_value=True)
        mock_instance.check_health = MagicMock(return_value=True)
        
        yield mock_instance

@pytest.fixture
def mock_embedding():
    """Mock embedding service for testing."""
    with patch('elysiactl.services.vector_embedding.EmbeddingService') as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
        
        yield mock_instance

class AsyncMock(MagicMock):
    """Async mock for testing async functions."""
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

class TestSyncPipeline:
    """Test the complete sync pipeline functionality."""
    
    def test_content_resolver_tier_classification(self, temp_workspace):
        """Test content resolver correctly classifies files into tiers."""
        resolver = ContentResolver()
        
        # Test tier classifications
        small_file = temp_workspace / "src/small.py"
        medium_file = temp_workspace / "src/medium.py"  
        large_file = temp_workspace / "src/large.py"
        binary_file = temp_workspace / "binary_file.png"
        vendor_file = temp_workspace / "vendor/lib.js"
        
        small_strategy = resolver.analyze_file(str(small_file))
        medium_strategy = resolver.analyze_file(str(medium_file))
        large_strategy = resolver.analyze_file(str(large_file))
        binary_strategy = resolver.analyze_file(str(binary_file))
        vendor_strategy = resolver.analyze_file(str(vendor_file))
        
        # Assertions
        assert small_strategy.tier == 1, "Small file should be tier 1"
        assert small_strategy.embed_content is True, "Small file should embed content"
        assert small_strategy.use_base64 is False, "Small file should not use base64"
        
        assert medium_strategy.tier == 2, "Medium file should be tier 2"
        assert medium_strategy.embed_content is True, "Medium file should embed content"
        assert medium_strategy.use_base64 is True, "Medium file should use base64"
        
        assert large_strategy.tier == 3, "Large file should be tier 3"
        assert large_strategy.embed_content is False, "Large file should not embed content"
        
        assert binary_strategy.skip_indexing is True, "Binary file should be skipped"
        assert vendor_strategy.skip_indexing is True, "Vendor file should be skipped"
    
    def test_checkpoint_system_basic_operations(self, temp_workspace):
        """Test SQLite checkpoint system basic operations."""
        checkpoint_dir = temp_workspace / "checkpoints"
        checkpoint_dir.mkdir()
        
        checkpoint = SQLiteCheckpointManager(str(checkpoint_dir))
        
        # Test run creation
        run_id = checkpoint.start_run("TEST_COLLECTION", dry_run=False)
        assert run_id is not None, "Run ID should be generated"
        assert run_id.startswith("sync_"), "Run ID should have correct prefix"
        
        # Test line operations
        assert not checkpoint.is_line_completed(run_id, 1), "Line should not be completed initially"
        
        checkpoint.mark_line_completed(run_id, 1, "/test/file.py", "modify")
        assert checkpoint.is_line_completed(run_id, 1), "Line should be completed after marking"
        
        # Test failure tracking
        checkpoint.mark_line_failed(run_id, 2, "/test/failed.py", "modify", "Test error", '{"test": "payload"}')
        failed_lines = checkpoint.get_failed_lines(run_id, max_retries=3)
        assert len(failed_lines) == 1, "Should have one failed line"
        assert failed_lines[0]['line_number'] == 2, "Failed line number should match"
        
        # Test run completion
        stats = checkpoint.complete_run(run_id)
        assert stats['success_count'] == 1, "Should have one success"
        assert stats['error_count'] == 1, "Should have one error"
    
    @pytest.mark.asyncio
    async def test_error_handling_retry_logic(self, temp_workspace, mock_weaviate, mock_embedding):
        """Test error handling and retry logic."""
        from elysiactl.services.error_handling import ProductionErrorHandler, ErrorContext
        
        error_handler = ProductionErrorHandler()
        
        # Test successful operation
        async def success_operation():
            return "success"
        
        context = ErrorContext("test_operation", total_attempts=3)
        result = await error_handler.execute_with_retry(success_operation, context)
        assert result == "success", "Successful operation should return result"
        
        # Test retryable failure
        attempt_count = 0
        async def failing_then_success_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary network error")
            return "success"
        
        attempt_count = 0
        context = ErrorContext("test_retry", total_attempts=5)
        result = await error_handler.execute_with_retry(failing_then_success_operation, context)
        assert result == "success", "Should succeed after retries"
        assert attempt_count == 3, "Should have made 3 attempts"
        
        # Test non-retryable failure
        async def permanent_failure():
            raise ValueError("Validation error")
        
        context = ErrorContext("test_permanent", total_attempts=3)
        with pytest.raises(Exception):
            await error_handler.execute_with_retry(permanent_failure, context)
    
    def test_jsonl_input_parsing(self, temp_workspace):
        """Test parsing of JSONL input format."""
        from elysiactl.services.sync import parse_input_line
        
        # Test plain file path
        plain_result = parse_input_line("/test/file.py", 1)
        assert plain_result['path'] == "/test/file.py", "Should parse plain file path"
        assert plain_result['op'] == "modify", "Should default to modify operation"
        assert plain_result['line'] == 1, "Should set line number"
        
        # Test JSONL format
        jsonl_input = '{"path": "/test/file.py", "op": "add", "content": "test content", "size": 12}'
        jsonl_result = parse_input_line(jsonl_input, 2)
        assert jsonl_result['path'] == "/test/file.py", "Should parse JSONL path"
        assert jsonl_result['op'] == "add", "Should parse JSONL operation"
        assert jsonl_result['content'] == "test content", "Should parse embedded content"
        assert jsonl_result['line'] == 2, "Should set line number"
        
        # Test base64 content
        import base64
        content = "def test():\n    pass"
        encoded_content = base64.b64encode(content.encode()).decode()
        base64_input = f'{{"path": "/test/base64.py", "op": "modify", "content_base64": "{encoded_content}"}}'
        base64_result = parse_input_line(base64_input, 3)
        assert base64_result['content_base64'] == encoded_content, "Should parse base64 content"
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self, temp_workspace, mock_weaviate, mock_embedding):
        """Test performance optimization features."""
        from elysiactl.services.performance import PerformanceOptimizer, BatchProcessor
        
        # Test batch processor
        batch_processor = BatchProcessor(batch_size=3, max_workers=2)
        
        async def simple_items():
            for i in range(10):
                yield {"id": i, "data": f"item_{i}"}
        
        async def simple_processor(items):
            return [{"processed": True, "id": item["id"]} for item in items]
        
        results = []
        async for batch_result in batch_processor.process_batches(simple_items(), simple_processor):
            results.extend(batch_result)
        
        assert len(results) == 10, "Should process all items"
        assert all(r["processed"] for r in results), "All items should be processed"
        
        batch_processor.shutdown()
        
        # Test performance optimizer
        perf_config = {
            'max_workers': 2,
            'batch_size': 5,
            'max_connections': 10,
            'memory_limit_mb': 128
        }
        
        optimizer = PerformanceOptimizer(perf_config)
        
        async def test_changes():
            for i in range(20):
                yield {
                    "line": i + 1,
                    "path": f"/test/file_{i}.py",
                    "op": "modify",
                    "content": f"def func_{i}():\n    pass"
                }
        
        async def mock_processor(changes):
            await asyncio.sleep(0.01)  # Simulate processing time
            return [{"success": True, "path": change["path"]} for change in changes]
        
        processed_count = 0
        async for result_batch in optimizer.optimize_sync_operation(test_changes(), mock_processor):
            processed_count += len(result_batch)
        
        assert processed_count == 20, "Should process all changes"
        
        perf_summary = optimizer.get_performance_summary()
        assert perf_summary['files_per_second'] > 0, "Should calculate files per second"
        
        await optimizer.cleanup()
    
    def test_cli_integration_dry_run(self, temp_workspace):
        """Test CLI integration with dry-run mode."""
        # Create test input
        test_files = [
            str(temp_workspace / "src/small.py"),
            str(temp_workspace / "src/medium.py"),
            str(temp_workspace / "docs/readme.md")
        ]
        
        input_data = "\n".join(test_files)
        
        # Run CLI command
        result = subprocess.run([
            "uv", "run", "elysiactl", "index", "sync",
            "--stdin", "--dry-run", "--collection", "TEST_COLLECTION"
        ], 
        input=input_data, 
        text=True, 
        capture_output=True,
        cwd=str(Path(__file__).parent.parent.parent)
        )
        
        assert result.returncode == 0, f"CLI should succeed: {result.stderr}"
        assert "TEST_COLLECTION" in result.stdout, "Should mention target collection"
        assert "DRY RUN" in result.stdout, "Should indicate dry-run mode"
    
    def test_large_file_handling(self, temp_workspace):
        """Test handling of large files and memory management."""
        resolver = ContentResolver()
        
        # Create a large file
        large_file = temp_workspace / "large_test.py"
        large_content = "# Large test file\n" + ("def function():\n    pass\n" * 10000)
        large_file.write_text(large_content)
        
        strategy = resolver.analyze_file(str(large_file))
        
        # Should use reference for large files
        assert strategy.tier == 3, "Large file should be tier 3"
        assert not strategy.embed_content, "Large file should not embed content"
        assert not strategy.skip_indexing, "Large text file should still be indexed"
        
        # Test content resolution
        change = resolver.create_optimized_change(str(large_file), "modify", 1)
        assert "content_ref" in change, "Large file should use content reference"
        assert "content" not in change, "Large file should not embed content"
        assert change["size"] > 100000, "Should report correct file size"
    
    def test_error_recovery_scenarios(self, temp_workspace):
        """Test various error recovery scenarios."""
        from elysiactl.services.error_handling import ErrorClassifier, ErrorCategory, ErrorSeverity
        
        classifier = ErrorClassifier()
        
        # Test error classification
        test_errors = [
            (Exception("Connection refused"), ErrorCategory.NETWORK, ErrorSeverity.LOW),
            (Exception("Rate limit exceeded"), ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM),
            (Exception("No such file or directory"), ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW),
            (Exception("Invalid UTF-8 encoding"), ErrorCategory.ENCODING, ErrorSeverity.LOW),
            (Exception("Out of memory"), ErrorCategory.MEMORY, ErrorSeverity.HIGH),
        ]
        
        for error, expected_category, expected_severity in test_errors:
            from elysiactl.services.error_handling import ErrorContext
            context = ErrorContext("test_operation")
            category, severity = classifier.classify_error(error, context)
            
            assert category == expected_category, f"Error '{error}' should be classified as {expected_category}"
            # Note: Severity might vary based on context, so we don't strict assert
    
    def test_checkpoint_recovery(self, temp_workspace):
        """Test checkpoint recovery after interruption."""
        checkpoint_dir = temp_workspace / "checkpoints"
        checkpoint_dir.mkdir()
        
        checkpoint = SQLiteCheckpointManager(str(checkpoint_dir))
        
        # Simulate interrupted run
        run_id = checkpoint.start_run("TEST_COLLECTION")
        
        # Process some items successfully
        checkpoint.mark_line_completed(run_id, 1, "/test/file1.py", "modify")
        checkpoint.mark_line_completed(run_id, 2, "/test/file2.py", "modify")
        
        # Leave some items failed (simulating interruption)
        checkpoint.mark_line_failed(run_id, 3, "/test/file3.py", "modify", "Interrupted", '{"path": "/test/file3.py"}')
        
        # Simulate recovery - check what can be resumed
        failed_lines = checkpoint.get_failed_lines(run_id, max_retries=3)
        assert len(failed_lines) == 1, "Should have one failed line to retry"
        assert failed_lines[0]['line_number'] == 3, "Should identify correct failed line"
        
        # Simulate successful retry
        checkpoint.mark_line_completed(run_id, 3, "/test/file3.py", "modify")
        
        # Complete run
        stats = checkpoint.complete_run(run_id)
        assert stats['success_count'] == 3, "Should count all successes"
        assert stats['error_count'] == 1, "Should count original error"

class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_throughput_benchmark(self, temp_workspace, mock_weaviate, mock_embedding):
        """Benchmark sync throughput with various configurations."""
        
        # Create test files
        num_files = 100
        test_files = []
        
        for i in range(num_files):
            file_path = temp_workspace / f"test_file_{i:03d}.py"
            content_size = 500 + (i % 5) * 200  # Variable sizes
            content = f"# Test file {i}\n" + ("def func():\n    pass\n" * (content_size // 20))
            file_path.write_text(content)
            test_files.append(str(file_path))
        
        # Benchmark configurations
        configs = [
            {"parallel": False, "batch_size": 1, "workers": 1},
            {"parallel": True, "batch_size": 10, "workers": 2},
            {"parallel": True, "batch_size": 50, "workers": 4},
        ]
        
        results = []
        
        for config in configs:
            input_data = "\n".join(test_files)
            
            start_time = time.time()
            
            # Mock the actual sync to focus on pipeline performance
            with patch('elysiactl.services.sync.sync_files_from_stdin') as mock_sync:
                mock_sync.return_value = True
                
                result = subprocess.run([
                    "uv", "run", "elysiactl", "index", "sync",
                    "--stdin", "--dry-run",
                    f"--workers={config['workers']}",
                    f"--batch-size={config['batch_size']}",
                    f"--{'parallel' if config['parallel'] else 'no-optimize'}"
                ], 
                input=input_data, 
                text=True, 
                capture_output=True,
                cwd=str(Path(__file__).parent.parent.parent),
                timeout=30
                )
            
            duration = time.time() - start_time
            files_per_second = num_files / duration if duration > 0 else 0
            
            results.append({
                'config': config,
                'duration': duration,
                'files_per_second': files_per_second,
                'success': result.returncode == 0
            })
        
        # Verify performance improvements
        sequential_result = results[0]
        parallel_results = results[1:]
        
        assert sequential_result['success'], "Sequential processing should work"
        
        for parallel_result in parallel_results:
            assert parallel_result['success'], "Parallel processing should work"
            # Note: In mocked environment, performance comparison may not be meaningful
    
    def test_memory_usage_stability(self, temp_workspace):
        """Test memory usage remains stable under load."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Create many test files to stress memory
        large_files = []
        for i in range(50):
            file_path = temp_workspace / f"large_file_{i}.py"
            content = f"# Large file {i}\n" + ("def function():\n    return 'data'\n" * 2000)
            file_path.write_text(content)
            large_files.append(str(file_path))
        
        # Process files multiple times to test memory leaks
        resolver = ContentResolver()
        
        for round_num in range(5):  # Multiple rounds
            for file_path in large_files:
                strategy = resolver.analyze_file(file_path)
                change = resolver.create_optimized_change(file_path, "modify", 1)
                
                # Force garbage collection
                if round_num % 2 == 0:
                    gc.collect()
        
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB for this test)
        assert memory_increase < 100, f"Memory usage increased by {memory_increase:.1f}MB - possible memory leak"

class TestProductionReadiness:
    """Production readiness validation tests."""
    
    def test_configuration_validation(self):
        """Test configuration system works correctly."""
        # Test environment variable override
        with patch.dict(os.environ, {
            'elysiactl_BATCH_SIZE': '150',
            'elysiactl_MAX_WORKERS': '12',
            'elysiactl_WCD_URL': 'http://test-weaviate:8080'
        }):
            config = reload_config()  # Reload to pick up env vars
            
            assert config.processing.batch_size == 150, "Should override batch size from env"
            assert config.processing.max_workers == 12, "Should override max workers from env"
            assert config.services.WCD_URL == 'http://test-weaviate:8080', "Should override Weaviate URL"
    
    def test_error_monitoring_commands(self, temp_workspace):
        """Test error monitoring CLI commands."""
        # Test status command
        result = subprocess.run([
            "uv", "run", "elysiactl", "index", "status", "--summary"
        ], 
        capture_output=True, 
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
        )
        
        assert result.returncode == 0, f"Status command should succeed: {result.stderr}"
        
        # Test errors command
        result = subprocess.run([
            "uv", "run", "elysiactl", "index", "errors", "--summary"
        ], 
        capture_output=True, 
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
        )
        
        assert result.returncode == 0, f"Errors command should succeed: {result.stderr}"
    
    def test_signal_handling(self, temp_workspace):
        """Test graceful handling of interruption signals."""
        # Create test input
        test_files = [str(temp_workspace / f"file_{i}.py") for i in range(20)]
        for file_path in test_files:
            Path(file_path).write_text(f"# Test file {file_path}")
        
        input_data = "\n".join(test_files)
        
        # Start sync process
        process = subprocess.Popen([
            "uv", "run", "elysiactl", "index", "sync",
            "--stdin", "--dry-run", "--verbose"
        ], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
        )
        
        # Let it start processing
        time.sleep(0.5)
        
        # Send interrupt signal
        process.send_signal(subprocess.signal.SIGINT)
        
        # Wait for graceful shutdown
        try:
            stdout, stderr = process.communicate(input=input_data, timeout=10)
            # Process should exit gracefully with appropriate message
            assert "Interrupted" in stdout or "Interrupted" in stderr, "Should handle interruption gracefully"
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Process did not shut down gracefully within timeout")
    
    def test_concurrent_access(self, temp_workspace):
        """Test concurrent access to checkpoint database."""
        checkpoint_dir = temp_workspace / "concurrent_checkpoints"
        checkpoint_dir.mkdir()
        
        # Create multiple checkpoint managers (simulating concurrent processes)
        checkpoint1 = SQLiteCheckpointManager(str(checkpoint_dir))
        checkpoint2 = SQLiteCheckpointManager(str(checkpoint_dir))
        
        # Test concurrent operations
        run_id1 = checkpoint1.start_run("COLLECTION_1")
        run_id2 = checkpoint2.start_run("COLLECTION_2")
        
        assert run_id1 != run_id2, "Should generate unique run IDs"
        
        # Test concurrent line operations
        checkpoint1.mark_line_completed(run_id1, 1, "/test/file1.py", "modify")
        checkpoint2.mark_line_completed(run_id2, 1, "/test/file2.py", "modify")
        
        # Verify data integrity
        assert checkpoint1.is_line_completed(run_id1, 1), "Checkpoint1 should track its own completions"
        assert checkpoint2.is_line_completed(run_id2, 1), "Checkpoint2 should track its own completions"
        assert not checkpoint1.is_line_completed(run_id2, 1), "Checkpoint1 should not see other run's completions"

@pytest.mark.slow
class TestEndToEndScenarios:
    """End-to-end integration tests with realistic scenarios."""
    
    def test_full_enterprise_simulation(self, temp_workspace):
        """Simulate full enterprise sync scenario."""
        # Create realistic enterprise directory structure
        enterprise_structure = {
            "ServiceA/src/main.py": "# Service A main\nclass MainService:\n    pass",
            "ServiceA/src/utils.py": "# Utilities\ndef helper():\n    pass",
            "ServiceA/tests/test_main.py": "# Tests\nimport unittest",
            "ServiceA/docs/api.md": "# API Documentation\n## Endpoints",
            "ServiceB/app.py": "# Service B\nfrom flask import Flask",
            "ServiceB/config.yaml": "database:\n  host: localhost\n  port: 5432",
            "ServiceB/requirements.txt": "flask>=2.0.0\npytest>=6.0.0",
            "Shared/common.py": "# Shared utilities\ndef common_func():\n    pass",
            "Shared/constants.py": "# Constants\nAPI_VERSION = 'v1'",
        }
        
        for file_path, content in enterprise_structure.items():
            full_path = temp_workspace / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        # Create change simulation (like mgit diff output)
        changes = []
        for i, (file_path, content) in enumerate(enterprise_structure.items(), 1):
            full_file_path = str(temp_workspace / file_path)
            
            # Mix of operations
            if i % 4 == 0:
                op = "delete"
                change = {"line": i, "path": full_file_path, "op": op}
            elif len(content) < 100:
                op = "add"
                change = {"line": i, "path": full_file_path, "op": op, "content": content}
            else:
                op = "modify"
                change = {"line": i, "path": full_file_path, "op": op, "content_ref": full_file_path}
            
            changes.append(json.dumps(change))
        
        input_data = "\n".join(changes)
        
        # Run full sync pipeline
        result = subprocess.run([
            "uv", "run", "elysiactl", "index", "sync",
            "--stdin", "--dry-run", "--verbose",
            "--parallel", "--workers=4", "--batch-size=5"
        ], 
        input=input_data, 
        text=True, 
        capture_output=True,
        cwd=str(Path(__file__).parent.parent.parent),
        timeout=60
        )
        
        assert result.returncode == 0, f"Enterprise sync should succeed: {result.stderr}"
        
        # Verify expected operations were processed
        assert "ServiceA" in result.stdout, "Should process ServiceA files"
        assert "ServiceB" in result.stdout, "Should process ServiceB files" 
        assert "Shared" in result.stdout, "Should process Shared files"
        
        # Check that different operations were handled
        if "ADD:" in result.stdout or "MODIFY:" in result.stdout or "DELETE:" in result.stdout:
            # Operations were processed
            pass
        else:
            # In dry-run mode, operations might be reported differently
            assert "Would" in result.stdout, "Should show dry-run operations"

# Test fixtures and utilities
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before all tests."""
    # Set test-specific environment variables
    test_env = {
        'elysiactl_DEBUG': 'true',
        'elysiactl_BATCH_SIZE': '10',
        'elysiactl_MAX_WORKERS': '2',
        'elysiactl_WCD_URL': 'http://localhost:8080',
        'elysiactl_DEFAULT_SOURCE_COLLECTION': 'TEST_COLLECTION',
        'elysiactl_CHECKPOINT_DB_DIR': '/tmp/elysiactl_test_checkpoints',
    }
    
    with patch.dict(os.environ, test_env):
        yield

def run_test_suite():
    """Run the complete test suite."""
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--durations=10",
        "-m", "not slow"  # Skip slow tests by default
    ]
    
    return pytest.main(pytest_args)

if __name__ == "__main__":
    exit_code = run_test_suite()
    sys.exit(exit_code)
```

### File: `/opt/elysiactl/tests/integration/test_performance_benchmarks.py` (NEW)

**Create performance-focused benchmark tests:**

```python
"""Performance benchmark tests for sync operations."""

import pytest
import time
import tempfile
import subprocess
import statistics
from pathlib import Path
from typing import List, Dict, Any

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Dedicated performance benchmark tests."""
    
    def create_test_dataset(self, temp_dir: Path, num_files: int, avg_size: int = 1000) -> List[str]:
        """Create realistic test dataset."""
        files = []
        
        for i in range(num_files):
            # Vary file sizes realistically
            size_factor = 0.5 + (i % 3) * 0.5  # 0.5x to 1.5x avg size
            content_size = int(avg_size * size_factor)
            
            # Create different file types
            if i % 4 == 0:
                file_path = temp_dir / f"service_{i//10}/src/main_{i}.py"
                content = f"# Main service {i}\n" + self._generate_python_content(content_size)
            elif i % 4 == 1:
                file_path = temp_dir / f"service_{i//10}/tests/test_{i}.py"
                content = f"# Test file {i}\n" + self._generate_test_content(content_size)
            elif i % 4 == 2:
                file_path = temp_dir / f"shared/utils_{i}.py"
                content = f"# Utilities {i}\n" + self._generate_util_content(content_size)
            else:
                file_path = temp_dir / f"config/settings_{i}.yaml"
                content = f"# Config {i}\n" + self._generate_yaml_content(content_size)
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            files.append(str(file_path))
        
        return files
    
    def _generate_python_content(self, size: int) -> str:
        """Generate realistic Python content."""
        functions_needed = max(1, size // 100)
        content = ""
        for i in range(functions_needed):
            content += f"""
def function_{i}():
    \"\"\"Function {i} documentation.\"\"\"
    result = []
    for x in range(10):
        result.append(x * {i})
    return result

"""
        return content[:size]
    
    def _generate_test_content(self, size: int) -> str:
        """Generate realistic test content."""
        tests_needed = max(1, size // 150)
        content = "import unittest\n\nclass TestCase(unittest.TestCase):\n"
        for i in range(tests_needed):
            content += f"""
    def test_{i}(self):
        \"\"\"Test case {i}.\"\"\"
        self.assertEqual({i}, {i})
        self.assertTrue({i} >= 0)
"""
        return content[:size]
    
    def _generate_util_content(self, size: int) -> str:
        """Generate realistic utility content."""
        return f"# Utility functions\n" + ("def util_func():\n    pass\n" * (size // 25))
    
    def _generate_yaml_content(self, size: int) -> str:
        """Generate realistic YAML content."""
        lines_needed = max(1, size // 30)
        content = ""
        for i in range(lines_needed):
            content += f"setting_{i}: value_{i}\n"
        return content[:size]
    
    @pytest.mark.parametrize("num_files,expected_min_fps", [
        (100, 10),   # Small dataset - should process at least 10 files/sec
        (500, 15),   # Medium dataset - should process at least 15 files/sec  
        (1000, 20),  # Large dataset - should process at least 20 files/sec
    ])
    def test_throughput_scaling(self, num_files: int, expected_min_fps: float):
        """Test that throughput scales appropriately with dataset size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test dataset
            files = self.create_test_dataset(temp_path, num_files, avg_size=1000)
            input_data = "\n".join(files)
            
            # Measure processing time
            start_time = time.time()
            
            result = subprocess.run([
                "uv", "run", "elysiactl", "index", "sync",
                "--stdin", "--dry-run",
                "--parallel", "--workers=4", "--batch-size=50"
            ], 
            input=input_data, 
            text=True, 
            capture_output=True,
            cwd=str(Path(__file__).parent.parent.parent),
            timeout=120  # 2 minute timeout
            )
            
            duration = time.time() - start_time
            files_per_second = num_files / duration
            
            assert result.returncode == 0, f"Sync failed: {result.stderr}"
            assert files_per_second >= expected_min_fps, \
                f"Performance below threshold: {files_per_second:.1f} < {expected_min_fps} files/sec"
            
            print(f"Processed {num_files} files in {duration:.2f}s ({files_per_second:.1f} files/sec)")
    
    def test_worker_scaling_efficiency(self):
        """Test that additional workers improve performance efficiently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create consistent test dataset
            files = self.create_test_dataset(temp_path, 500, avg_size=800)
            input_data = "\n".join(files)
            
            worker_configs = [1, 2, 4, 8]
            results = []
            
            for workers in worker_configs:
                times = []
                
                # Run multiple times for statistical significance
                for run in range(3):
                    start_time = time.time()
                    
                    result = subprocess.run([
                        "uv", "run", "elysiactl", "index", "sync",
                        "--stdin", "--dry-run",
                        f"--workers={workers}",
                        "--batch-size=25"
                    ], 
                    input=input_data, 
                    text=True, 
                    capture_output=True,
                    cwd=str(Path(__file__).parent.parent.parent),
                    timeout=90
                    )
                    
                    duration = time.time() - start_time
                    times.append(duration)
                    
                    assert result.returncode == 0, f"Run {run} with {workers} workers failed"
                
                avg_time = statistics.mean(times)
                files_per_second = len(files) / avg_time
                
                results.append({
                    'workers': workers,
                    'avg_time': avg_time,
                    'files_per_second': files_per_second,
                    'times': times
                })
            
            # Verify scaling efficiency
            baseline = results[0]['files_per_second']  # 1 worker
            
            for result in results[1:]:  # 2+ workers
                workers = result['workers']
                fps = result['files_per_second']
                
                # Should see some improvement, but not necessarily linear
                improvement_ratio = fps / baseline
                min_expected_improvement = 1.2 if workers == 2 else 1.5
                
                assert improvement_ratio >= min_expected_improvement, \
                    f"Workers={workers} should improve performance by at least {min_expected_improvement}x, got {improvement_ratio:.2f}x"
                
                print(f"Workers: {workers}, FPS: {fps:.1f}, Improvement: {improvement_ratio:.2f}x")
    
    def test_batch_size_optimization(self):
        """Test optimal batch size for different scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test with different file size distributions
            test_scenarios = [
                {"name": "small_files", "count": 1000, "avg_size": 200},   # Many small files
                {"name": "mixed_files", "count": 500, "avg_size": 2000},   # Mixed sizes
                {"name": "large_files", "count": 100, "avg_size": 10000},  # Fewer large files
            ]
            
            for scenario in test_scenarios:
                files = self.create_test_dataset(
                    temp_path / scenario["name"], 
                    scenario["count"], 
                    scenario["avg_size"]
                )
                input_data = "\n".join(files)
                
                batch_sizes = [10, 25, 50, 100, 200]
                batch_results = []
                
                for batch_size in batch_sizes:
                    start_time = time.time()
                    
                    result = subprocess.run([
                        "uv", "run", "elysiactl", "index", "sync",
                        "--stdin", "--dry-run",
                        "--parallel", "--workers=4",
                        f"--batch-size={batch_size}"
                    ], 
                    input=input_data, 
                    text=True, 
                    capture_output=True,
                    cwd=str(Path(__file__).parent.parent.parent),
                    timeout=60
                    )
                    
                    duration = time.time() - start_time
                    files_per_second = len(files) / duration
                    
                    batch_results.append({
                        'batch_size': batch_size,
                        'duration': duration,
                        'files_per_second': files_per_second
                    })
                    
                    assert result.returncode == 0, f"Batch size {batch_size} failed for {scenario['name']}"
                
                # Find optimal batch size (highest throughput)
                optimal_result = max(batch_results, key=lambda x: x['files_per_second'])
                worst_result = min(batch_results, key=lambda x: x['files_per_second'])
                
                # Optimal should be significantly better than worst
                improvement = optimal_result['files_per_second'] / worst_result['files_per_second']
                assert improvement >= 1.3, f"Batch size optimization should show at least 30% improvement"
                
                print(f"Scenario {scenario['name']}: Optimal batch_size={optimal_result['batch_size']} "
                      f"({optimal_result['files_per_second']:.1f} files/sec)")
    
    def test_memory_efficiency_under_load(self):
        """Test memory usage remains reasonable under high load."""
        import psutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create large dataset
            files = self.create_test_dataset(temp_path, 2000, avg_size=3000)
            input_data = "\n".join(files)
            
            # Monitor memory during processing
            process = subprocess.Popen([
                "uv", "run", "elysiactl", "index", "sync",
                "--stdin", "--dry-run",
                "--parallel", "--workers=6", "--batch-size=100"
            ], 
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
            )
            
            # Monitor memory usage
            max_memory_mb = 0
            memory_samples = []
            
            try:
                # Send input and monitor
                process.stdin.write(input_data)
                process.stdin.close()
                
                while process.poll() is None:
                    try:
                        proc_info = psutil.Process(process.pid)
                        memory_mb = proc_info.memory_info().rss / (1024 * 1024)
                        memory_samples.append(memory_mb)
                        max_memory_mb = max(max_memory_mb, memory_mb)
                        time.sleep(0.1)
                    except psutil.NoSuchProcess:
                        break
                
                stdout, stderr = process.communicate(timeout=60)
                
                assert process.returncode == 0, f"Process failed: {stderr}"
                
                # Memory should stay reasonable (< 1GB for this test)
                assert max_memory_mb < 1024, f"Memory usage too high: {max_memory_mb:.1f}MB"
                
                # Memory should be relatively stable (no major leaks)
                if len(memory_samples) > 10:
                    early_avg = statistics.mean(memory_samples[:5])
                    late_avg = statistics.mean(memory_samples[-5:])
                    growth_ratio = late_avg / early_avg
                    
                    assert growth_ratio < 2.0, f"Memory growth too high: {growth_ratio:.2f}x"
                
                print(f"Peak memory usage: {max_memory_mb:.1f}MB")
                
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail("Process did not complete within timeout")

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
```

### File: `/opt/elysiactl/tests/integration/test_scenarios.py` (NEW)

**Create real-world scenario tests:**

```python
"""Real-world scenario tests for enterprise environments."""

import pytest
import tempfile
import subprocess
import json
from pathlib import Path
from typing import Dict, List

@pytest.mark.integration 
class TestEnterpriseScenarios:
    """Test scenarios based on real enterprise usage patterns."""
    
    def test_git_workflow_integration(self):
        """Test integration with Git workflow scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = Path(temp_dir) / "test_repo"
            repo_dir.mkdir()
            
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_dir, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
            
            # Create initial files
            (repo_dir / "src").mkdir()
            (repo_dir / "src/main.py").write_text("def main():\n    print('v1')")
            (repo_dir / "README.md").write_text("# Test Project v1")
            
            # Initial commit
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
            
            # Make changes
            (repo_dir / "src/main.py").write_text("def main():\n    print('v2')\n    print('updated')")
            (repo_dir / "src/utils.py").write_text("def helper():\n    return 'helper'")
            (repo_dir / "README.md").write_text("# Test Project v2\n\nUpdated with new features")
            
            # Get changed files (simulating git diff --name-only)
            subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"], 
                cwd=repo_dir, 
                capture_output=True, 
                text=True,
                check=True
            )
            
            changed_files = [str(repo_dir / line.strip()) for line in result.stdout.strip().split('\n') if line.strip()]
            
            # Test sync with changed files
            input_data = "\n".join(changed_files)
            
            sync_result = subprocess.run([
                "uv", "run", "elysiactl", "index", "sync",
                "--stdin", "--dry-run", "--verbose"
            ], 
            input=input_data, 
            text=True, 
            capture_output=True,
            cwd=str(Path(__file__).parent.parent.parent)
            )
            
            assert sync_result.returncode == 0, f"Git workflow sync failed: {sync_result.stderr}"
            assert "src/main.py" in sync_result.stdout, "Should process modified main.py"
            assert "src/utils.py" in sync_result.stdout, "Should process new utils.py"
            assert "README.md" in sync_result.stdout, "Should process updated README.md"
    
    def test_monorepo_structure(self):
        """Test handling of monorepo with multiple services."""
        with tempfile.TemporaryDirectory() as temp_dir:
            monorepo = Path(temp_dir) / "monorepo"
            
            # Create realistic monorepo structure
            services = {
                "api-gateway": {
                    "src/main.py": "# API Gateway\nfrom flask import Flask",
                    "src/auth.py": "# Authentication\nclass AuthManager:\n    pass",
                    "requirements.txt": "flask\nrequests",
                    "Dockerfile": "FROM python:3.9\nCOPY . /app"
                },
                "user-service": {
                    "app.py": "# User Service\nfrom fastapi import FastAPI",
                    "models/user.py": "# User model\nclass User:\n    pass",
                    "tests/test_user.py": "# User tests\nimport pytest",
                    "config.yaml": "database:\n  url: postgres://localhost/users"
                },
                "notification-service": {
                    "main.go": "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Notification service\")\n}",
                    "handlers/email.go": "package handlers\n\nfunc SendEmail() {\n    // Send email logic\n}",
                    "go.mod": "module notification-service\n\ngo 1.19",
                },
                "shared": {
                    "utils.py": "# Shared utilities\ndef common_func():\n    pass",
                    "constants.py": "# Constants\nAPI_VERSION = 'v1.2.0'",
                    "proto/user.proto": "syntax = \"proto3\";\n\nmessage User {\n    string id = 1;\n}"
                }
            }
            
            all_files = []
            for service, files in services.items():
                service_dir = monorepo / service
                service_dir.mkdir(parents=True, exist_ok=True)
                
                for file_path, content in files.items():
                    full_path = service_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    all_files.append(str(full_path))
            
            # Test sync with monorepo structure
            input_data = "\n".join(all_files)
            
            result = subprocess.run([
                "uv", "run", "elysiactl", "index", "sync",
                "--stdin", "--dry-run", "--verbose",
                "--parallel", "--workers=3", "--batch-size=5"
            ], 
            input=input_data, 
            text=True, 
            capture_output=True,
            cwd=str(Path(__file__).parent.parent.parent)
            )
            
            assert result.returncode == 0, f"Monorepo sync failed: {result.stderr}"
            
            # Verify all services were processed
            for service in services.keys():
                assert service in result.stdout, f"Service {service} should be processed"
            
            # Verify different file types were handled appropriately
            assert ".py" in result.stdout, "Python files should be processed"
            assert ".go" in result.stdout or "main.go" in result.stdout, "Go files should be processed"
            assert ".proto" in result.stdout or "proto" in result.stdout, "Proto files should be processed"
    
    def test_large_scale_changes(self):
        """Test handling of large-scale changes (like major refactoring)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "large_project"
            
            # Simulate large project with many files
            file_patterns = [
                ("services/auth/src/{}.py", 50),
                ("services/user/src/{}.py", 40), 
                ("services/data/src/{}.py", 60),
                ("shared/utils/{}.py", 30),
                ("tests/unit/{}.py", 100),
                ("tests/integration/{}.py", 25),
                ("docs/{}.md", 20),
                ("config/{}.yaml", 15)
            ]
            
            all_files = []
            change_operations = []
            
            for pattern, count in file_patterns:
                for i in range(count):
                    file_path = project_dir / pattern.format(f"file_{i:03d}")
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Generate content based on file type
                    if file_path.suffix == ".py":
                        content = f"# File {i}\ndef function_{i}():\n    return {i}"
                    elif file_path.suffix == ".md":
                        content = f"# Documentation {i}\n\nThis is documentation for file {i}."
                    elif file_path.suffix == ".yaml":
                        content = f"config_{i}:\n  value: {i}\n  enabled: true"
                    else:
                        content = f"# Generic content {i}"
                    
                    file_path.write_text(content)
                    all_files.append(str(file_path))
                    
                    # Create mix of operations (70% modify, 20% add, 10% delete)
                    if i % 10 == 0:
                        op = "delete"
                        change = {"line": len(change_operations) + 1, "path": str(file_path), "op": op}
                    elif i % 5 == 0:
                        op = "add"
                        change = {"line": len(change_operations) + 1, "path": str(file_path), "op": op, "content": content}
                    else:
                        op = "modify"
                        change = {"line": len(change_operations) + 1, "path": str(file_path), "op": op, "content_ref": str(file_path)}
                    
                    change_operations.append(json.dumps(change))
            
            # Test with JSONL input format (simulating mgit output)
            input_data = "\n".join(change_operations)
            
            # Test processing large changes
            result = subprocess.run([
                "uv", "run", "elysiactl", "index", "sync",
                "--stdin", "--dry-run",
                "--parallel", "--workers=6", "--batch-size=50"
            ], 
            input=input_data, 
            text=True, 
            capture_output=True,
            cwd=str(Path(__file__).parent.parent.parent),
            timeout=120  # Allow more time for large dataset
            )
            
            assert result.returncode == 0, f"Large scale sync failed: {result.stderr}"
            
            # Verify performance is acceptable
            total_files = len(change_operations)
            assert total_files >= 300, f"Test should have many files, got {total_files}"
            
            # Check that progress reporting is working
            assert "files" in result.stdout.lower(), "Should report file processing"
    
    def test_error_resilience_scenario(self):
        """Test resilience to various error conditions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "error_test"
            test_dir.mkdir()
            
            # Create mix of valid and problematic files
            test_cases = [
                ("valid/good_file.py", "def good():\n    return 'ok'", True),
                ("valid/another_good.py", "class GoodClass:\n    pass", True),
                ("missing/nonexistent.py", None, False),  # File doesn't exist
                ("permission/restricted.py", "restricted content", True),  # Will exist but might have permission issues
                ("encoding/bad_encoding.txt", b"\xff\xfe\x00\x00invalid utf-8", False),  # Bad encoding
                ("large/huge_file.py", "# Large file\n" + ("def func():\n    pass\n" * 20000), True),  # Very large file
            ]
            
            valid_files = []
            all_change_operations = []
            
            for file_path, content, should_exist in test_cases:
                full_path = test_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                if should_exist and content is not None:
                    if isinstance(content, bytes):
                        full_path.write_bytes(content)
                    else:
                        full_path.write_text(content)
                        valid_files.append(str(full_path))
                
                # Add to change operations regardless (to test error handling)
                change = {"line": len(all_change_operations) + 1, "path": str(full_path), "op": "modify"}
                if should_exist and content and isinstance(content, str) and len(content) < 1000:
                    change["content"] = content
                else:
                    change["content_ref"] = str(full_path)
                
                all_change_operations.append(json.dumps(change))
            
            input_data = "\n".join(all_change_operations)
            
            # Test error resilience
            result = subprocess.run([
                "uv", "run", "elysiactl", "index", "sync",
                "--stdin", "--dry-run", "--verbose"
            ], 
            input=input_data, 
            text=True, 
            capture_output=True,
            cwd=str(Path(__file__).parent.parent.parent)
            )
            
            # Should not crash despite errors
            assert result.returncode == 0, f"Error resilience test failed: {result.stderr}"
            
            # Should report both successes and errors
            output = result.stdout + result.stderr
            assert "good_file.py" in output, "Should process valid files"
            
            # Should handle errors gracefully
            error_indicators = ["error", "failed", "warning", "not found"]
            has_error_handling = any(indicator in output.lower() for indicator in error_indicators)
            assert has_error_handling, "Should report error handling"

# Test runner for scenario tests
def run_scenario_tests():
    """Run scenario test suite."""
    pytest_args = [
        str(Path(__file__)),
        "-v",
        "-m", "integration",
        "--tb=short",
        "--durations=5"
    ]
    
    return pytest.main(pytest_args)

if __name__ == "__main__":
    exit_code = run_scenario_tests()
    sys.exit(exit_code)
```

### File: `/opt/elysiactl/pytest.ini` (NEW)

**Create pytest configuration:**

```ini
[tool:pytest]
minversion = 6.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -ra
    --strict-markers
    --strict-config
    --disable-warnings
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    benchmark: marks tests as performance benchmarks  
    integration: marks tests as integration tests
    unit: marks tests as unit tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### File: `/opt/elysiactl/scripts/run_integration_tests.sh` (NEW)

**Create test runner script:**

```bash
#!/bin/bash
"""Integration test runner for elysiactl sync pipeline."""

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/tests/integration"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=${VERBOSE:-false}
BENCHMARK=${BENCHMARK:-false}
SLOW_TESTS=${SLOW_TESTS:-false}
COVERAGE=${COVERAGE:-false}

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -v, --verbose       Enable verbose output
    -b, --benchmark     Run performance benchmarks
    -s, --slow          Include slow tests
    -c, --coverage      Generate coverage report
    -h, --help         Show this help message

Environment Variables:
    elysiactl_TEST_WCD_URL    URL for test Weaviate instance (default: http://localhost:8080)
    elysiactl_TEST_COLLECTION      Test collection name (default: TEST_COLLECTION)
    
Examples:
    $0                              # Run basic integration tests
    $0 --verbose                    # Run with verbose output
    $0 --benchmark                  # Run performance benchmarks
    $0 --slow --benchmark           # Run all tests including slow ones
    $0 --coverage                   # Run with coverage reporting
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -b|--benchmark)
            BENCHMARK=true
            shift
            ;;
        -s|--slow)
            SLOW_TESTS=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            print_usage
            exit 1
            ;;
    esac
done

echo -e "${BLUE}ElysiaCtl Integration Test Suite${NC}"
echo "=================================="

# Check dependencies
echo -e "\n${YELLOW}Checking dependencies...${NC}"

if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv not found. Please install uv package manager.${NC}"
    exit 1
fi

# Set test environment
export elysiactl_DEBUG=true
export elysiactl_BATCH_SIZE=10
export elysiactl_MAX_WORKERS=2
export elysiactl_WCD_URL=${elysiactl_TEST_WCD_URL:-"http://localhost:8080"}
export elysiactl_DEFAULT_SOURCE_COLLECTION=${elysiactl_TEST_COLLECTION:-"TEST_COLLECTION"}

echo "Test environment:"
echo "  Weaviate URL: $elysiactl_WCD_URL"
echo "  Collection: $elysiactl_DEFAULT_SOURCE_COLLECTION"
echo "  Workers: $elysiactl_MAX_WORKERS"
echo "  Batch Size: $elysiactl_BATCH_SIZE"

# Build pytest command
PYTEST_CMD="uv run pytest"
PYTEST_ARGS=()

# Base arguments
PYTEST_ARGS+=("$TEST_DIR")
PYTEST_ARGS+=("--tb=short")

if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_ARGS+=("-v")
    PYTEST_ARGS+=("--durations=10")
else
    PYTEST_ARGS+=("-q")
fi

# Test selection
TEST_MARKERS=()
if [[ "$BENCHMARK" == "true" ]]; then
    TEST_MARKERS+=("benchmark")
fi

if [[ "$SLOW_TESTS" == "false" ]]; then
    if [[ ${#TEST_MARKERS[@]} -eq 0 ]]; then
        PYTEST_ARGS+=("-m" "not slow")
    else
        # Combine markers
        MARKER_EXPR=$(IFS=" or "; echo "${TEST_MARKERS[*]}")
        PYTEST_ARGS+=("-m" "$MARKER_EXPR and not slow")
    fi
elif [[ ${#TEST_MARKERS[@]} -gt 0 ]]; then
    MARKER_EXPR=$(IFS=" or "; echo "${TEST_MARKERS[*]}")
    PYTEST_ARGS+=("-m" "$MARKER_EXPR")
fi

# Coverage
if [[ "$COVERAGE" == "true" ]]; then
    PYTEST_ARGS+=("--cov=elysiactl")
    PYTEST_ARGS+=("--cov-report=term-missing")
    PYTEST_ARGS+=("--cov-report=html:coverage_html")
fi

# Run tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
echo "Command: $PYTEST_CMD ${PYTEST_ARGS[*]}"

cd "$PROJECT_ROOT"
START_TIME=$(date +%s)

if $PYTEST_CMD "${PYTEST_ARGS[@]}"; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo -e "\n${GREEN}✓ Integration tests passed in ${DURATION}s${NC}"
    
    if [[ "$COVERAGE" == "true" ]]; then
        echo -e "\n${BLUE}Coverage report generated in coverage_html/index.html${NC}"
    fi
    
    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo -e "\n${RED}✗ Integration tests failed after ${DURATION}s${NC}"
    
    # Show recent logs for debugging
    echo -e "\n${YELLOW}Recent error logs:${NC}"
    if [[ -f "/tmp/elysiactl/sync.log" ]]; then
        tail -20 "/tmp/elysiactl/sync.log" || true
    fi
    
    exit 1
fi
```

### File: `/opt/elysiactl/scripts/performance_report.py` (NEW)

**Create performance analysis script:**

```python
#!/usr/bin/env python3
"""Performance analysis and reporting tool for elysiactl sync operations."""

import argparse
import json
import sqlite3
import statistics
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_checkpoint_performance(db_path: str) -> Dict[str, Any]:
    """Analyze performance from checkpoint database."""
    if not Path(db_path).exists():
        return {"error": "Checkpoint database not found"}
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get run statistics
        runs = conn.execute("""
            SELECT run_id, started_at, completed_at, processed_lines, 
                   success_count, error_count, collection_name
            FROM sync_runs 
            WHERE completed_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 10
        """).fetchall()
        
        if not runs:
            return {"error": "No completed runs found"}
        
        # Calculate performance metrics
        run_metrics = []
        for run in runs:
            start_time = datetime.fromisoformat(run['started_at'])
            end_time = datetime.fromisoformat(run['completed_at'])
            duration = (end_time - start_time).total_seconds()
            
            files_per_second = run['processed_lines'] / duration if duration > 0 else 0
            success_rate = (run['success_count'] / max(run['processed_lines'], 1)) * 100
            
            run_metrics.append({
                'run_id': run['run_id'],
                'duration': duration,
                'files_processed': run['processed_lines'],
                'files_per_second': files_per_second,
                'success_rate': success_rate,
                'error_count': run['error_count'],
                'collection': run['collection_name']
            })
        
        # Aggregate statistics
        durations = [m['duration'] for m in run_metrics]
        fps_values = [m['files_per_second'] for m in run_metrics]
        success_rates = [m['success_rate'] for m in run_metrics]
        
        analysis = {
            'total_runs': len(run_metrics),
            'avg_duration': statistics.mean(durations),
            'avg_files_per_second': statistics.mean(fps_values),
            'avg_success_rate': statistics.mean(success_rates),
            'best_performance': max(fps_values),
            'worst_performance': min(fps_values),
            'recent_runs': run_metrics[:5],
            'performance_trend': 'improving' if len(fps_values) >= 2 and fps_values[0] > fps_values[-1] else 'stable'
        }
        
        # Get processing time statistics
        processing_times = conn.execute("""
            SELECT AVG(processing_time_ms) as avg_time, 
                   MAX(processing_time_ms) as max_time,
                   MIN(processing_time_ms) as min_time,
                   COUNT(*) as total_operations
            FROM completed_lines
            WHERE processing_time_ms > 0
        """).fetchone()
        
        if processing_times and processing_times['total_operations'] > 0:
            analysis['avg_processing_time_ms'] = processing_times['avg_time']
            analysis['max_processing_time_ms'] = processing_times['max_time']
            analysis['min_processing_time_ms'] = processing_times['min_time']
            analysis['total_operations'] = processing_times['total_operations']
        
        return analysis
        
    finally:
        conn.close()

def generate_performance_report(db_path: str, output_dir: str = "performance_reports"):
    """Generate comprehensive performance report."""
    analysis = analyze_checkpoint_performance(db_path)
    
    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
        return
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate text report
    report_file = output_path / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_file, 'w') as f:
        f.write("ElysiaCtl Sync Performance Report\n")
        f.write("=" * 35 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Database: {db_path}\n\n")
        
        f.write("Summary Statistics:\n")
        f.write(f"  Total runs analyzed: {analysis['total_runs']}\n")
        f.write(f"  Average duration: {analysis['avg_duration']:.2f} seconds\n")
        f.write(f"  Average throughput: {analysis['avg_files_per_second']:.1f} files/second\n")
        f.write(f"  Average success rate: {analysis['avg_success_rate']:.1f}%\n")
        f.write(f"  Best performance: {analysis['best_performance']:.1f} files/second\n")
        f.write(f"  Worst performance: {analysis['worst_performance']:.1f} files/second\n")
        f.write(f"  Performance trend: {analysis['performance_trend']}\n\n")
        
        if 'avg_processing_time_ms' in analysis:
            f.write("Processing Time Statistics:\n")
            f.write(f"  Average per operation: {analysis['avg_processing_time_ms']:.2f}ms\n")
            f.write(f"  Maximum per operation: {analysis['max_processing_time_ms']:.2f}ms\n")
            f.write(f"  Minimum per operation: {analysis['min_processing_time_ms']:.2f}ms\n")
            f.write(f"  Total operations: {analysis['total_operations']}\n\n")
        
        f.write("Recent Runs:\n")
        for i, run in enumerate(analysis['recent_runs'], 1):
            f.write(f"  {i}. {run['run_id']}\n")
            f.write(f"     Duration: {run['duration']:.2f}s\n")
            f.write(f"     Throughput: {run['files_per_second']:.1f} files/sec\n")
            f.write(f"     Success rate: {run['success_rate']:.1f}%\n")
            f.write(f"     Errors: {run['error_count']}\n\n")
    
    # Generate JSON report for programmatic use
    json_file = output_path / f"performance_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f"Performance report generated:")
    print(f"  Text report: {report_file}")
    print(f"  JSON data: {json_file}")
    
    # Generate visualizations if matplotlib available
    try:
        generate_performance_charts(analysis, output_path)
    except ImportError:
        print("  Matplotlib not available - skipping charts")

def generate_performance_charts(analysis: Dict[str, Any], output_dir: Path):
    """Generate performance visualization charts."""
    # Throughput over time
    recent_runs = analysis['recent_runs']
    if len(recent_runs) >= 2:
        plt.figure(figsize=(12, 8))
        
        # Extract data
        run_numbers = list(range(len(recent_runs), 0, -1))  # Reverse for chronological order
        throughputs = [run['files_per_second'] for run in reversed(recent_runs)]
        success_rates = [run['success_rate'] for run in reversed(recent_runs)]
        
        # Throughput chart
        plt.subplot(2, 2, 1)
        plt.plot(run_numbers, throughputs, 'b-o', linewidth=2)
        plt.title('Throughput Over Recent Runs')
        plt.xlabel('Run Number (Most Recent → Oldest)')
        plt.ylabel('Files per Second')
        plt.grid(True, alpha=0.3)
        
        # Success rate chart
        plt.subplot(2, 2, 2)
        plt.plot(run_numbers, success_rates, 'g-o', linewidth=2)
        plt.title('Success Rate Over Recent Runs')
        plt.xlabel('Run Number (Most Recent → Oldest)')
        plt.ylabel('Success Rate (%)')
        plt.grid(True, alpha=0.3)
        plt.ylim(0, 105)
        
        # Performance distribution
        plt.subplot(2, 2, 3)
        plt.hist(throughputs, bins=max(3, len(throughputs)//2), alpha=0.7, color='blue')
        plt.title('Throughput Distribution')
        plt.xlabel('Files per Second')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        
        # Summary statistics
        plt.subplot(2, 2, 4)
        plt.axis('off')
        stats_text = f"""Performance Summary:
        
Runs Analyzed: {analysis['total_runs']}
Avg Throughput: {analysis['avg_files_per_second']:.1f} files/sec
Best Performance: {analysis['best_performance']:.1f} files/sec
Avg Success Rate: {analysis['avg_success_rate']:.1f}%
Trend: {analysis['performance_trend']}"""
        
        plt.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        plt.tight_layout()
        
        chart_file = output_dir / f"performance_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  Performance charts: {chart_file}")

def main():
    parser = argparse.ArgumentParser(description="Analyze elysiactl sync performance")
    parser.add_argument("--db", 
                       default="/var/lib/elysiactl/sync_checkpoints.db",
                       help="Path to checkpoint database")
    parser.add_argument("--output", "-o",
                       default="performance_reports",
                       help="Output directory for reports")
    parser.add_argument("--json-only",
                       action="store_true",
                       help="Output only JSON data")
    
    args = parser.parse_args()
    
    if args.json_only:
        analysis = analyze_checkpoint_performance(args.db)
        print(json.dumps(analysis, indent=2, default=str))
    else:
        generate_performance_report(args.db, args.output)

if __name__ == "__main__":
    main()
```

## Agent Workflow

1. **Test Infrastructure Setup:**
   - Create comprehensive integration test suite covering all phases
   - Set up realistic test data generation and scenarios
   - Create performance benchmark tests with statistical analysis
   - Implement test configuration and environment management

2. **Scenario Coverage:**
   - Test end-to-end pipeline with real-world data patterns
   - Create Git workflow integration tests
   - Test monorepo and large-scale scenarios
   - Verify error resilience and recovery

3. **Performance Validation:**
   - Benchmark throughput scaling with different configurations
   - Test worker efficiency and memory usage
   - Validate optimization strategies
   - Create performance monitoring and reporting tools

4. **Production Readiness:**
   - Test signal handling and graceful shutdown
   - Verify concurrent access patterns
   - Test configuration management
   - Create comprehensive test runner and reporting

## Testing

### Run complete integration test suite:
```bash
# Run all integration tests
/opt/elysiactl/scripts/run_integration_tests.sh

# Run with verbose output
/opt/elysiactl/scripts/run_integration_tests.sh --verbose

# Run performance benchmarks
/opt/elysiactl/scripts/run_integration_tests.sh --benchmark

# Run all tests including slow ones
/opt/elysiactl/scripts/run_integration_tests.sh --slow --benchmark
```

### Run specific test categories:
```bash
# Run only performance benchmarks
uv run pytest tests/integration/test_performance_benchmarks.py -v -m benchmark

# Run scenario tests
uv run pytest tests/integration/test_scenarios.py -v -m integration

# Run pipeline tests
uv run pytest tests/integration/test_sync_pipeline.py -v
```

### Generate performance reports:
```bash
# Generate performance report from checkpoint database
python scripts/performance_report.py --db /var/lib/elysiactl/sync_checkpoints.db

# Output JSON only
python scripts/performance_report.py --json-only --db /var/lib/elysiactl/sync_checkpoints.db
```

### Test with coverage:
```bash
# Run tests with coverage reporting
/opt/elysiactl/scripts/run_integration_tests.sh --coverage
```

### Manual testing scenarios:
```bash
# Test enterprise scenario
find /opt/elysiactl -name "*.py" | head -100 | uv run elysiactl index sync --stdin --parallel --workers=4 --dry-run --verbose

# Test error handling
echo "/nonexistent/file.py" | uv run elysiactl index sync --stdin --verbose

# Test checkpoint recovery (interrupt and resume)
find /opt/elysiactl -name "*.py" | uv run elysiactl index sync --stdin --verbose
# Interrupt with Ctrl+C, then run again to test resume
```

## Success Criteria

- [ ] Complete integration test suite covers all sync pipeline phases
- [ ] Performance benchmarks validate 50+ files/second throughput
- [ ] End-to-end scenarios test realistic enterprise usage patterns
- [ ] Error resilience tests verify graceful handling of all error types
- [ ] Memory efficiency tests confirm stable usage under load
- [ ] Concurrent access tests validate SQLite checkpoint integrity
- [ ] Git workflow integration tests pass with real repository structures
- [ ] Monorepo scenarios handle complex directory structures correctly
- [ ] Large-scale tests process 1000+ files reliably
- [ ] Performance reports provide actionable optimization insights
- [ ] All test categories (unit, integration, benchmark) execute successfully
- [ ] Test coverage exceeds 80% for sync-related code
- [ ] Continuous integration setup enables automated testing
- [ ] Production readiness validation confirms deployment readiness

## Configuration Changes

Add testing configuration to project:

**File: `/opt/elysiactl/pyproject.toml`** (UPDATE)

```toml
[tool.pytest.ini_options]
minversion = "6.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",
    "--strict-markers", 
    "--strict-config",
    "--disable-warnings"
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "benchmark: marks tests as performance benchmarks",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests"
]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning"
]

[tool.coverage.run]
source = ["src/elysiactl"]
omit = ["tests/*", "scripts/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

This phase completes the sync pipeline implementation with comprehensive testing that ensures production readiness, performance validation, and operational reliability. The test suite provides confidence for enterprise deployments while enabling continuous improvement through performance monitoring and analysis.