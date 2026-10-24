"""
FIN SIGHT AI - Backup & Recovery System
Provides automated and manual backup creation, checksum verification,
retention policies, and safe restore workflows.
Excludes secrets, credentials, virtual environments, and caches.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Excluded directory names
EXCLUDED_DIRS = {
    ".git",
    "venv",
    ".venv",
    "env",
    ".pytest_cache",
    "__pycache__",
    ".tempmediaStorage",
    ".streamlit",
    ".idea",
    ".vscode",
    "backups",
}

# Excluded file extensions & filenames (secrets, locks, large binaries)
EXCLUDED_PATTERNS = {
    ".env",
    ".env.local",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    "*.tmp",
    "*.swp",
}


@dataclass
class BackupManifest:
    """Metadata describing a project backup."""
    backup_id: str
    created_at: str
    app_name: str = "FIN SIGHT AI"
    app_version: str = "2.1.0"
    backup_type: str = "manual"  # manual, auto_pre_upgrade, auto_pre_restore, scheduled
    description: str = ""
    archive_filename: str = ""
    archive_size_bytes: int = 0
    archive_sha256: str = ""
    total_files: int = 0
    included_files: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "valid"  # valid, corrupted, restored
    database_included: bool = False
    notes: str = ""


class BackupManager:
    """
    Manages project backup archives and safe recovery workflows for FIN SIGHT AI.
    """

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        backup_dir: Optional[str] = None,
    ):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.backup_dir = Path(backup_dir or (self.workspace_root / "backups")).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_catalog_path = self.backup_dir / "backup_catalog.json"
        self._init_catalog()

    def _init_catalog(self) -> None:
        """Initialize manifest catalog file if missing."""
        if not self.manifest_catalog_path.exists():
            with open(self.manifest_catalog_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def _load_catalog(self) -> List[Dict[str, Any]]:
        try:
            with open(self.manifest_catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Error reading backup catalog: %s. Reinitializing.", exc)
            return []

    def _save_catalog(self, catalog: List[Dict[str, Any]]) -> None:
        with open(self.manifest_catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)

    @staticmethod
    def compute_sha256(filepath: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def is_path_eligible(self, path: Path) -> bool:
        """Check if a file should be included in the backup."""
        rel_parts = path.relative_to(self.workspace_root).parts

        # Check excluded directories
        for part in rel_parts[:-1]:
            if part in EXCLUDED_DIRS:
                return False

        filename = path.name
        # Never backup secret environment files
        if filename == ".env" or filename.startswith(".env."):
            return False
        if filename.endswith((".pyc", ".pyo", ".log", ".tmp")):
            return False

        return True

    def collect_backup_files(self) -> List[Path]:
        """Collect all eligible files in the workspace for backup."""
        eligible_files: List[Path] = []

        # Key directories & files to explicitly check
        target_roots = [
            self.workspace_root / "src",
            self.workspace_root / "pages",
            self.workspace_root / "data",
            self.workspace_root / "docs",
            self.workspace_root / "reports",
            self.workspace_root / "tests",
        ]

        top_files = [
            "app.py",
            "requirements.txt",
            "pytest.ini",
            "Dockerfile",
            "docker-compose.yml",
            ".dockerignore",
            "README.md",
            ".env.example",
            "generate_sample_pdf.py",
        ]

        for tf in top_files:
            fp = self.workspace_root / tf
            if fp.exists() and self.is_path_eligible(fp):
                eligible_files.append(fp)

        for tr in target_roots:
            if tr.exists():
                for root, dirs, files in os.walk(tr):
                    # Filter out excluded dirs in-place
                    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                    for file in files:
                        fp = Path(root) / file
                        if self.is_path_eligible(fp):
                            eligible_files.append(fp)

        return sorted(list(set(eligible_files)))

    def create_backup(
        self,
        description: str = "Manual backup",
        backup_type: str = "manual",
    ) -> BackupManifest:
        """
        Create a new timestamped backup archive of the project.
        """
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")[:19]
        backup_id = f"backup_{timestamp_str}"
        archive_name = f"{backup_id}.zip"
        archive_path = self.backup_dir / archive_name

        eligible_files = self.collect_backup_files()
        file_metadata_list: List[Dict[str, Any]] = []
        has_database = False

        # Create zip archive
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in eligible_files:
                try:
                    rel_path = file_path.relative_to(self.workspace_root).as_posix()
                    file_sha = self.compute_sha256(file_path)
                    file_size = file_path.stat().st_size
                    zf.write(file_path, arcname=rel_path)

                    if rel_path.endswith(".db"):
                        has_database = True

                    file_metadata_list.append({
                        "path": rel_path,
                        "size_bytes": file_size,
                        "sha256": file_sha,
                    })
                except Exception as exc:
                    logger.warning("Could not add %s to backup: %s", file_path, exc)

            # Write manifest JSON inside the archive
            archive_manifest = {
                "backup_id": backup_id,
                "created_at": now.isoformat(),
                "app_name": "FIN SIGHT AI",
                "app_version": "2.1.0",
                "backup_type": backup_type,
                "description": description,
                "total_files": len(file_metadata_list),
                "database_included": has_database,
                "files": file_metadata_list,
            }
            zf.writestr("backup_manifest.json", json.dumps(archive_manifest, indent=2))

        archive_size = archive_path.stat().st_size
        archive_sha = self.compute_sha256(archive_path)

        manifest = BackupManifest(
            backup_id=backup_id,
            created_at=now.isoformat(),
            app_name="FIN SIGHT AI",
            app_version="2.1.0",
            backup_type=backup_type,
            description=description,
            archive_filename=archive_name,
            archive_size_bytes=archive_size,
            archive_sha256=archive_sha,
            total_files=len(file_metadata_list),
            included_files=file_metadata_list,
            status="valid",
            database_included=has_database,
            notes=f"Successfully backed up {len(file_metadata_list)} files.",
        )

        # Update catalog
        catalog = self._load_catalog()
        catalog.append(asdict(manifest))
        self._save_catalog(catalog)

        logger.info(
            "Backup %s created successfully (%d files, %.2f MB)",
            backup_id,
            len(file_metadata_list),
            archive_size / (1024 * 1024),
        )
        return manifest

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups from catalog with verification of archive presence."""
        catalog = self._load_catalog()
        valid_list = []
        for item in catalog:
            archive_path = self.backup_dir / item.get("archive_filename", "")
            item["exists_on_disk"] = archive_path.exists()
            valid_list.append(item)
        return sorted(valid_list, key=lambda x: x.get("created_at", ""), reverse=True)

    def verify_backup(self, backup_id: str) -> Tuple[bool, str, List[str]]:
        """
        Verify the integrity of a backup archive against catalog SHA-256 and test internal file extraction.

        Returns:
            Tuple of (is_valid, message, list_of_warnings_or_errors)
        """
        catalog = self._load_catalog()
        entry = next((b for b in catalog if b["backup_id"] == backup_id), None)
        if not entry:
            return False, f"Backup {backup_id} not found in catalog.", ["Missing catalog record"]

        archive_path = self.backup_dir / entry.get("archive_filename", "")
        if not archive_path.exists():
            return False, f"Backup archive {archive_path.name} not found on disk.", ["Missing zip file"]

        # 1. Verify archive file checksum
        calculated_sha = self.compute_sha256(archive_path)
        if calculated_sha != entry.get("archive_sha256"):
            return (
                False,
                f"Checksum mismatch for {backup_id}: expected {entry.get('archive_sha256')[:12]}..., got {calculated_sha[:12]}...",
                ["Archive file corrupted or modified"],
            )

        # 2. Test zip file integrity and verify each file's checksum
        errors: List[str] = []
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Test zip CRC
                bad_file = zf.testzip()
                if bad_file:
                    errors.append(f"Corrupted file in zip archive: {bad_file}")

                # Check internal manifest
                if "backup_manifest.json" not in zf.namelist():
                    errors.append("Archive missing internal backup_manifest.json")

                manifest_bytes = zf.read("backup_manifest.json")
                internal_manifest = json.loads(manifest_bytes.decode("utf-8"))

                # Verify each file's individual checksum
                for f_info in internal_manifest.get("files", []):
                    rel_p = f_info["path"]
                    if rel_p in zf.namelist():
                        file_data = zf.read(rel_p)
                        sha = hashlib.sha256(file_data).hexdigest()
                        if sha != f_info["sha256"]:
                            errors.append(f"Checksum mismatch in archived file: {rel_p}")
                    else:
                        errors.append(f"Declared file missing from archive: {rel_p}")

        except Exception as exc:
            errors.append(f"Failed to read zip archive: {exc}")

        is_valid = len(errors) == 0
        status_msg = "Backup verified: Integrity check passed." if is_valid else "Backup integrity verification failed."
        return is_valid, status_msg, errors

    def restore_backup(
        self,
        backup_id: str,
        create_pre_restore_backup: bool = True,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Safely restore the project from a selected backup.
        1. Validates backup integrity.
        2. Creates an automatic pre-restore backup of current state.
        3. Safely extracts files over workspace.
        4. Validates database consistency if database exists.
        5. Reports outcome.

        Returns:
            Tuple of (success, message, details_dict)
        """
        details: Dict[str, Any] = {
            "backup_id": backup_id,
            "pre_restore_backup_id": None,
            "restored_files_count": 0,
            "database_checked": False,
            "health_check_passed": False,
        }

        # Step 1: Verify backup integrity
        is_valid, msg, errors = self.verify_backup(backup_id)
        if not is_valid:
            logger.error("Restore aborted: Backup %s failed verification: %s", backup_id, errors)
            return False, f"Restore aborted: {msg} ({'; '.join(errors)})", details

        # Step 2: Create pre-restore safety backup
        if create_pre_restore_backup:
            try:
                pre_backup = self.create_backup(
                    description=f"Auto safety backup before restoring {backup_id}",
                    backup_type="auto_pre_restore",
                )
                details["pre_restore_backup_id"] = pre_backup.backup_id
                logger.info("Created pre-restore safety backup: %s", pre_backup.backup_id)
            except Exception as exc:
                return False, f"Failed to create pre-restore safety backup: {exc}", details

        # Step 3: Extract files safely
        catalog = self._load_catalog()
        entry = next((b for b in catalog if b["backup_id"] == backup_id), None)
        archive_path = self.backup_dir / entry.get("archive_filename", "")

        restored_count = 0
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                for member in zf.namelist():
                    if member == "backup_manifest.json":
                        continue

                    # Prevent zip-slip
                    target_path = (self.workspace_root / member).resolve()
                    if not str(target_path).startswith(str(self.workspace_root)):
                        logger.warning("Skipping suspicious zip-slip path: %s", member)
                        continue

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, open(target_path, "wb") as dest:
                        shutil.copyfileobj(source, dest)
                    restored_count += 1

            details["restored_files_count"] = restored_count
        except Exception as exc:
            logger.error("Error extracting backup archive: %s", exc)
            return False, f"Extraction failed: {exc}", details

        # Step 4: Verify database consistency if any .db exists
        for root, _, files in os.walk(self.workspace_root / "data"):
            for f in files:
                if f.endswith(".db"):
                    db_p = Path(root) / f
                    try:
                        conn = sqlite3.connect(db_p)
                        cursor = conn.cursor()
                        cursor.execute("PRAGMA integrity_check")
                        result = cursor.fetchone()
                        conn.close()
                        if result and result[0] == "ok":
                            details["database_checked"] = True
                        else:
                            return False, f"Database integrity check failed on {f}: {result}", details
                    except Exception as db_exc:
                        return False, f"Database verification error on {f}: {db_exc}", details

        # Step 5: Application health checks (verify core files exist)
        essential_files = ["app.py", "requirements.txt", "src/graph/workflow.py"]
        for ef in essential_files:
            if not (self.workspace_root / ef).exists():
                return False, f"Health check failed: Missing essential file {ef} after restore", details

        details["health_check_passed"] = True

        logger.info("Successfully restored project from %s (%d files)", backup_id, restored_count)
        return True, f"Successfully restored {restored_count} files from {backup_id}.", details

    def enforce_retention_policy(self, max_backups: int = 15, max_age_days: int = 30) -> int:
        """
        Enforce backup retention policy by removing older backups exceeding limits.
        Always preserves at least 2 most recent backups regardless of age.
        """
        catalog = self._load_catalog()
        if len(catalog) <= 2:
            return 0

        # Sort newest first
        sorted_catalog = sorted(catalog, key=lambda x: x.get("created_at", ""), reverse=True)
        keep = sorted_catalog[:2]
        candidates = sorted_catalog[2:]

        now = datetime.now()
        removed_count = 0
        retained = list(keep)

        for item in candidates:
            # Check age
            created_at = datetime.fromisoformat(item["created_at"])
            age_days = (now - created_at).days
            should_remove = False

            if age_days > max_age_days:
                should_remove = True
            elif len(retained) >= max_backups:
                should_remove = True

            if should_remove:
                # Remove file from disk
                archive_p = self.backup_dir / item.get("archive_filename", "")
                if archive_p.exists():
                    try:
                        archive_p.unlink()
                    except Exception as e:
                        logger.warning("Could not delete archive %s: %e", archive_p, e)
                removed_count += 1
            else:
                retained.append(item)

        self._save_catalog(retained)
        logger.info("Enforced retention policy: Removed %d old backups, retained %d", removed_count, len(retained))
        return removed_count

    def export_backup_archive(self, backup_id: str) -> Optional[bytes]:
        """Read archive bytes for downloading/export."""
        catalog = self._load_catalog()
        entry = next((b for b in catalog if b["backup_id"] == backup_id), None)
        if not entry:
            return None
        archive_p = self.backup_dir / entry.get("archive_filename", "")
        if not archive_p.exists():
            return None
        return archive_p.read_bytes()
