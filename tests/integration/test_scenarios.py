"""Simplified scenario tests for enterprise environments."""

import pytest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

@pytest.mark.integration 
class TestEnterpriseScenarios:
    """Test scenarios based on real enterprise usage patterns."""
    
    def test_content_resolver_with_enterprise_patterns(self):
        """Test content resolver with realistic enterprise file patterns."""
        from elysiactl.services.content_resolver import ContentResolver
        
        resolver = ContentResolver()
        
        # Create test files that simulate enterprise patterns
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create enterprise-style directory structure
            test_files = {
                "src/main.py": "def main():\n    print('Main application')",
                "src/utils/helpers.py": "def helper():\n    return 'help'",
                "tests/test_main.py": "import unittest\n\nclass TestMain(unittest.TestCase):\n    pass",
                "node_modules/package.json": '{"name": "dependency"}',
                ".git/config": "[core]\n\trepositoryformatversion = 0",
                "vendor/library.js": "// Vendor library\nfunction vendor() {}",
                "build/output.txt": "Build output",
                "dist/app.js": "console.log('built app');",
                "docs/README.md": "# Project Documentation",
                "config/settings.yaml": "database:\n  host: localhost",
                "requirements.txt": "flask>=2.0.0\nrequests>=2.25.0",
                "Makefile": "all:\n\t@echo 'Building...'"
            }
            
            for file_path, content in test_files.items():
                full_path = workspace / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            # Test various file types
            test_cases = [
                ("src/main.py", "small source file"),
                ("node_modules/package.json", "node_modules should be skipped"),
                (".git/config", "git directory should be skipped"),
                ("vendor/library.js", "vendor directory should be skipped"),
                ("docs/README.md", "documentation should be indexed"),
                ("config/settings.yaml", "config file should be indexed"),
                ("requirements.txt", "requirements should be indexed")
            ]
            
            for file_path, description in test_cases:
                full_path = workspace / file_path
                analysis = resolver.analyze_file(str(full_path))
                
                if "should be skipped" in description:
                    assert analysis.is_skippable, f"{description} - {file_path}"
                elif "should be indexed" in description:
                    assert not analysis.is_skippable, f"{description} - {file_path}"
    
    def test_large_file_handling_in_enterprise_context(self):
        """Test large file handling with enterprise-scale files."""
        from elysiactl.services.content_resolver import ContentResolver
        
        resolver = ContentResolver()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create files of different sizes
            sizes_and_tiers = [
                (500, 1, "small file should be tier 1"),
                (50000, 2, "medium file should be tier 2"), 
                (5000000, 3, "large file should be tier 3")
            ]
            
            for size, expected_tier, description in sizes_and_tiers:
                # Create file with specified size
                content = "# Large file\n" + ("def func():\n    pass\n" * (size // 20))
                file_path = workspace / f"test_{size}.py"
                file_path.write_text(content)
                
                analysis = resolver.analyze_file(str(file_path))
                assert analysis.predicted_tier == expected_tier, f"{description} - got tier {analysis.predicted_tier}"
    
    def test_content_format_handling(self):
        """Test handling of different content formats."""
        from elysiactl.services.content_resolver import ContentResolver
        
        resolver = ContentResolver()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Test different content formats
            test_cases = [
                ("small.py", "def hello():\n    return 'world'", "small file should embed content"),
                ("medium.py", "# Medium file\n" + ("def func():\n    pass\n" * 500), "medium file should use base64"),
                ("large.py", "# Large file\n" + ("def func():\n    pass\n" * 10000), "large file should use reference")
            ]
            
            for filename, content, description in test_cases:
                file_path = workspace / filename
                file_path.write_text(content)
                
                analysis = resolver.analyze_file(str(file_path))
                
                if "should embed content" in description:
                    assert analysis.predicted_tier == 1
                    assert analysis.embed_content == True
                    assert analysis.use_base64 == False
                elif "should use base64" in description:
                    assert analysis.predicted_tier == 2
                    assert analysis.embed_content == True
                    assert analysis.use_base64 == True
                elif "should use reference" in description:
                    assert analysis.predicted_tier == 3
                    assert analysis.embed_content == False

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
