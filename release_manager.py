"""Release Management System - Version snapshots, deployment, and A/B testing."""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReleaseMetadata:
    """Metadata for a release version."""
    version: str
    timestamp: str
    description: str
    author: str
    components: Dict[str, str]  # Component name -> version hash
    test_results: Dict[str, Any]
    status: str  # "draft", "tested", "deployed", "rolled_back"
    notes: str = ""


class Release:
    """Represents a single agent version snapshot."""

    def __init__(
        self,
        version: str,
        description: str,
        author: str,
        skills_dir: str = "skills",
        db_path: str = "agent.db",
    ):
        """Initialize a new release."""
        self.version = version
        self.description = description
        self.author = author
        self.timestamp = datetime.now().isoformat()
        self.skills_dir = Path(skills_dir)
        self.db_path = Path(db_path)
        self.release_dir = Path("releases") / version
        self.metadata: Optional[ReleaseMetadata] = None

    def create_snapshot(self) -> bool:
        """Create a snapshot of current agent state."""
        try:
            # Create release directory
            self.release_dir.mkdir(parents=True, exist_ok=True)

            # Copy skills
            skills_snapshot = self.release_dir / "skills"
            if skills_snapshot.exists():
                shutil.rmtree(skills_snapshot)
            shutil.copytree(self.skills_dir, skills_snapshot)

            # Copy database
            if self.db_path.exists():
                shutil.copy(self.db_path, self.release_dir / "agent.db")

            # Create manifest
            manifest = {
                "version": self.version,
                "timestamp": self.timestamp,
                "description": self.description,
                "author": self.author,
                "status": "draft",
                "skills_count": len(list(skills_snapshot.glob("*.yaml"))),
                "created_at": self.timestamp,
            }

            with open(self.release_dir / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"✅ Snapshot created for version {self.version}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create snapshot: {str(e)}")
            return False

    def load_metadata(self) -> bool:
        """Load release metadata."""
        try:
            manifest_path = self.release_dir / "manifest.json"
            if not manifest_path.exists():
                logger.error(f"Manifest not found for version {self.version}")
                return False

            with open(manifest_path, "r") as f:
                data = json.load(f)

            self.metadata = ReleaseMetadata(
                version=data.get("version"),
                timestamp=data.get("timestamp"),
                description=data.get("description"),
                author=data.get("author"),
                components={},
                test_results={},
                status=data.get("status", "draft"),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load metadata: {str(e)}")
            return False

    def get_size(self) -> str:
        """Get total size of release."""
        if not self.release_dir.exists():
            return "0B"

        total = sum(f.stat().st_size for f in self.release_dir.rglob("*") if f.is_file())
        for unit in ["B", "KB", "MB", "GB"]:
            if total < 1024:
                return f"{total:.1f}{unit}"
            total /= 1024
        return f"{total:.1f}TB"


class ReleaseManager:
    """Manages agent releases, deployments, and A/B testing."""

    def __init__(self, releases_dir: str = "releases"):
        """Initialize release manager."""
        self.releases_dir = Path(releases_dir)
        self.releases_dir.mkdir(exist_ok=True)
        self.active_version: Optional[str] = None
        self.load_active_version()

    def load_active_version(self):
        """Load currently active release version."""
        active_file = self.releases_dir / ".active"
        if active_file.exists():
            with open(active_file, "r") as f:
                self.active_version = f.read().strip()

    def create_release(
        self, version: str, description: str, author: str
    ) -> Optional[Release]:
        """Create a new release version."""
        try:
            if (self.releases_dir / version).exists():
                logger.error(f"Version {version} already exists")
                return None

            release = Release(version, description, author)
            if release.create_snapshot():
                logger.info(f"✅ Release {version} created successfully")
                return release
            return None

        except Exception as e:
            logger.error(f"Failed to create release: {str(e)}")
            return None

    def list_releases(self) -> List[Dict[str, Any]]:
        """List all available releases."""
        releases = []
        for release_dir in sorted(self.releases_dir.glob("*/"), reverse=True):
            if release_dir.name.startswith("."):
                continue

            manifest_path = release_dir / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)

                is_active = release_dir.name == self.active_version
                releases.append({
                    "version": release_dir.name,
                    "timestamp": manifest.get("timestamp"),
                    "description": manifest.get("description"),
                    "author": manifest.get("author"),
                    "status": manifest.get("status"),
                    "active": is_active,
                    "size": self._get_dir_size(release_dir),
                })

        return releases

    def deploy_release(self, version: str) -> bool:
        """Deploy a release version."""
        try:
            release_dir = self.releases_dir / version
            if not release_dir.exists():
                logger.error(f"Release {version} not found")
                return False

            # Update active version
            active_file = self.releases_dir / ".active"
            with open(active_file, "w") as f:
                f.write(version)

            self.active_version = version

            # Update manifest status
            manifest_path = release_dir / "manifest.json"
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            manifest["status"] = "deployed"
            manifest["deployed_at"] = datetime.now().isoformat()

            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"✅ Deployed version {version}")
            return True

        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return False

    def rollback_release(self, version: str) -> bool:
        """Rollback to a previous release version."""
        try:
            release_dir = self.releases_dir / version
            if not release_dir.exists():
                logger.error(f"Release {version} not found")
                return False

            # Update active version
            active_file = self.releases_dir / ".active"
            with open(active_file, "w") as f:
                f.write(version)

            self.active_version = version

            # Update manifest status
            manifest_path = release_dir / "manifest.json"
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            manifest["status"] = "rolled_back"
            manifest["rolled_back_at"] = datetime.now().isoformat()

            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"✅ Rolled back to version {version}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False

    def compare_releases(self, version1: str, version2: str) -> Dict[str, Any]:
        """Compare two release versions."""
        comparison = {
            "version1": version1,
            "version2": version2,
            "differences": [],
            "skills_added": [],
            "skills_removed": [],
            "skills_modified": [],
        }

        try:
            v1_skills = set((self.releases_dir / version1 / "skills").glob("*.yaml"))
            v2_skills = set((self.releases_dir / version2 / "skills").glob("*.yaml"))

            v1_names = {s.stem for s in v1_skills}
            v2_names = {s.stem for s in v2_skills}

            comparison["skills_added"] = list(v2_names - v1_names)
            comparison["skills_removed"] = list(v1_names - v2_names)

            # Check for modifications
            for skill_name in v1_names & v2_names:
                s1 = self.releases_dir / version1 / "skills" / f"{skill_name}.yaml"
                s2 = self.releases_dir / version2 / "skills" / f"{skill_name}.yaml"

                if s1.read_text() != s2.read_text():
                    comparison["skills_modified"].append(skill_name)

            logger.info(f"Comparison: {version1} vs {version2}")
            return comparison

        except Exception as e:
            logger.error(f"Comparison failed: {str(e)}")
            return comparison

    def _get_dir_size(self, directory: Path) -> str:
        """Get directory size in human-readable format."""
        total = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
        for unit in ["B", "KB", "MB", "GB"]:
            if total < 1024:
                return f"{total:.1f}{unit}"
            total /= 1024
        return f"{total:.1f}TB"

    def get_active_release(self) -> Optional[Dict[str, Any]]:
        """Get currently active release info."""
        if not self.active_version:
            return None

        releases = self.list_releases()
        for release in releases:
            if release["version"] == self.active_version:
                return release

        return None
