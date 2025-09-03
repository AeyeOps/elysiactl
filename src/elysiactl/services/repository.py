"""Repository data management and JSONL file handling."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import jsonlines

@dataclass
class Repository:
    """Represents a repository from mgit discovery."""
    organization: str
    project: str
    repository: str
    clone_url: str
    ssh_url: str
    default_branch: str
    is_private: bool
    description: Optional[str]
    last_sync: Optional[datetime] = None
    sync_status: str = "unknown"  # unknown, success, failed, pending

    @property
    def full_name(self) -> str:
        """Get the full repository name (org/project/repo)."""
        return f"{self.organization}/{self.project}/{self.repository}"

    @property
    def display_name(self) -> str:
        """Get a display-friendly name."""
        return f"{self.organization}/{self.repository}"

class RepositoryService:
    """Service for managing repository data and mgit integration."""

    def __init__(self, data_dir: Path = None):
        """Initialize repository service."""
        self.data_dir = data_dir or Path.home() / ".elysiactl" / "repos"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.repositories: Dict[str, Repository] = {}

    def load_from_jsonl(self, jsonl_path: Path) -> List[Repository]:
        """Load repositories from mgit JSONL output file."""
        repositories = []

        try:
            with jsonlines.open(jsonl_path) as reader:
                for line in reader:
                    # Handle both mgit list format and diff-remote format
                    if 'organization' in line:
                        # mgit list format
                        repo = Repository(
                            organization=line['organization'],
                            project=line['project'],
                            repository=line['repository'],
                            clone_url=line['clone_url'],
                            ssh_url=line['ssh_url'],
                            default_branch=line['default_branch'],
                            is_private=line['is_private'],
                            description=line.get('description')
                        )
                        repositories.append(repo)
                        self.repositories[repo.full_name] = repo

        except Exception as e:
            print(f"Error loading JSONL file {jsonl_path}: {e}")

        return repositories

    def discover_repositories(self, pattern: str, provider: Optional[str] = None) -> List[Repository]:
        """Discover repositories using mgit and return Repository objects."""
        import subprocess
        import tempfile

        # Create temporary file for mgit output
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.jsonl', delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Build mgit command
            cmd = ['mgit', 'list', pattern, '--format', 'json']

            if provider:
                cmd.extend(['--provider', provider])

            # Redirect output to temporary file
            with open(tmp_path, 'w') as outfile:
                result = subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0:
                return self.load_from_jsonl(tmp_path)
            else:
                print(f"Error running mgit: {result.stderr}")
                return []

        finally:
            # Clean up temporary file
            tmp_path.unlink(missing_ok=True)

    def get_repository_status(self, repo: Repository) -> str:
        """Get the sync status for a repository."""
        # TODO: Implement actual status checking
        # For now, return mock status
        return "success"

    def update_repository_status(self, repo_name: str, status: str):
        """Update the sync status for a repository."""
        if repo_name in self.repositories:
            self.repositories[repo_name].sync_status = status
            self.repositories[repo_name].last_sync = datetime.now()

    def get_repositories_by_status(self, status: str) -> List[Repository]:
        """Get repositories filtered by sync status."""
        return [repo for repo in self.repositories.values() if repo.sync_status == status]

    def get_repositories_by_pattern(self, pattern: str) -> List[Repository]:
        """Get repositories matching a pattern."""
        # Simple pattern matching for now
        pattern_lower = pattern.lower()
        return [repo for repo in self.repositories.values()
                if pattern_lower in repo.organization.lower() or
                   pattern_lower in repo.repository.lower() or
                   pattern_lower in repo.project.lower()]

    def save_repository_config(self):
        """Save current repository configuration."""
        config_file = self.data_dir / "repositories.json"

        config = {
            'repositories': [
                {
                    'full_name': repo.full_name,
                    'organization': repo.organization,
                    'project': repo.project,
                    'repository': repo.repository,
                    'clone_url': repo.clone_url,
                    'ssh_url': repo.ssh_url,
                    'default_branch': repo.default_branch,
                    'is_private': repo.is_private,
                    'description': repo.description,
                    'last_sync': repo.last_sync.isoformat() if repo.last_sync else None,
                    'sync_status': repo.sync_status
                }
                for repo in self.repositories.values()
            ],
            'last_updated': datetime.now().isoformat()
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def load_repository_config(self):
        """Load repository configuration from disk."""
        config_file = self.data_dir / "repositories.json"

        if not config_file.exists():
            return

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            for repo_data in config.get('repositories', []):
                repo = Repository(
                    organization=repo_data['organization'],
                    project=repo_data['project'],
                    repository=repo_data['repository'],
                    clone_url=repo_data['clone_url'],
                    ssh_url=repo_data['ssh_url'],
                    default_branch=repo_data['default_branch'],
                    is_private=repo_data['is_private'],
                    description=repo_data.get('description'),
                    sync_status=repo_data.get('sync_status', 'unknown')
                )

                if repo_data.get('last_sync'):
                    repo.last_sync = datetime.fromisoformat(repo_data['last_sync'])

                self.repositories[repo.full_name] = repo

        except Exception as e:
            print(f"Error loading repository config: {e}")

# Global service instance
repo_service = RepositoryService()