"""
FIN SIGHT AI - Test Suite for Project Backup & Safe Restore
Verifies backup creation, catalog records, SHA-256 integrity, secret exclusion,
corruption detection, and safe pre-restore workflow.
"""
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
import pytest

from src.backup.backup_manager import BackupManager


class TestBackupAndRestore:
    """Test suite for backup and recovery system."""

    @pytest.fixture
    def test_env(self):
        # Create temporary workspace and backup dir
        temp_dir = tempfile.mkdtemp()
        ws_root = Path(temp_dir) / "workspace"
        ws_root.mkdir()
        backup_dir = Path(temp_dir) / "backups"

        # Create dummy project files
        (ws_root / "app.py").write_text("print('FIN SIGHT AI app')", encoding="utf-8")
        (ws_root / "requirements.txt").write_text("streamlit>=1.38.0", encoding="utf-8")
        (ws_root / ".env").write_text("SECRET_KEY=do_not_backup", encoding="utf-8")

        src_dir = ws_root / "src" / "graph"
        src_dir.mkdir(parents=True)
        (src_dir / "workflow.py").write_text("# workflow", encoding="utf-8")

        mgr = BackupManager(workspace_root=str(ws_root), backup_dir=str(backup_dir))

        yield {
            "root": ws_root,
            "backup_dir": backup_dir,
            "mgr": mgr,
        }

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_backup_creation_and_secret_exclusion(self, test_env):
        mgr: BackupManager = test_env["mgr"]
        manifest = mgr.create_backup(description="Test unit backup")

        assert manifest.backup_id.startswith("backup_")
        assert manifest.status == "valid"
        assert manifest.total_files >= 3

        # Verify .env was strictly excluded
        included_paths = [f["path"] for f in manifest.included_files]
        assert not any(".env" in p for p in included_paths)
        assert any("app.py" in p for p in included_paths)

    def test_integrity_verification_success(self, test_env):
        mgr: BackupManager = test_env["mgr"]
        manifest = mgr.create_backup(description="Integrity test")

        is_valid, msg, errors = mgr.verify_backup(manifest.backup_id)
        assert is_valid is True
        assert len(errors) == 0

    def test_corrupted_backup_detection(self, test_env):
        mgr: BackupManager = test_env["mgr"]
        manifest = mgr.create_backup(description="Corruption test")
        archive_path = test_env["backup_dir"] / manifest.archive_filename

        # Corrupt archive by appending garbage bytes
        with open(archive_path, "ab") as f:
            f.write(b"CORRUPTION_BYTES_GARBAGE")

        is_valid, msg, errors = mgr.verify_backup(manifest.backup_id)
        assert is_valid is False
        assert any("checksum" in err.lower() or "corrupt" in err.lower() for err in errors)

    def test_safe_restore_workflow(self, test_env):
        mgr: BackupManager = test_env["mgr"]
        ws_root = test_env["root"]

        # Create original backup
        manifest = mgr.create_backup(description="Baseline state")

        # Mutate app.py
        app_file = ws_root / "app.py"
        app_file.write_text("print('MODIFIED CONTENT')", encoding="utf-8")

        # Execute safe restore
        success, msg, details = mgr.restore_backup(
            manifest.backup_id, create_pre_restore_backup=True
        )

        assert success is True
        assert details["pre_restore_backup_id"] is not None
        assert details["health_check_passed"] is True

        # Check restored content
        restored_text = app_file.read_text(encoding="utf-8")
        assert "FIN SIGHT AI app" in restored_text

    def test_retention_policy_enforcement(self, test_env):
        mgr: BackupManager = test_env["mgr"]
        # Create 4 backups
        for i in range(4):
            mgr.create_backup(description=f"Snapshot {i}")

        assert len(mgr.list_backups()) == 4

        # Enforce max 2
        removed = mgr.enforce_retention_policy(max_backups=2)
        assert removed == 2
        assert len(mgr.list_backups()) == 2
