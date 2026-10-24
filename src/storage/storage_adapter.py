"""
FIN SIGHT AI - Storage Adapter Layer
Provides an abstraction over local filesystem and cloud object storage (AWS S3).
Enables stateless horizontal scaling and clean lifecycle management.
"""
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, List, Optional
from datetime import datetime

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class StorageAdapter(ABC):
    """Abstract interface for storing uploaded files, extracted indices, and reports."""

    @abstractmethod
    def save_file(self, file_bytes: bytes, destination_path: str) -> str:
        """Saves file bytes and returns accessible URI or local path."""
        pass

    @abstractmethod
    def get_file(self, path_or_uri: str) -> bytes:
        """Retrieves raw bytes of a stored file."""
        pass

    @abstractmethod
    def delete_file(self, path_or_uri: str) -> bool:
        """Removes a file from storage."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """Lists files matching the prefix."""
        pass

    @abstractmethod
    def cleanup_old_files(self, max_age_hours: int = 48) -> int:
        """Prunes stale temporary files to prevent unbounded disk growth."""
        pass


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage implementation for development and single-container setups."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path("data")
        self.uploads_dir = self.base_dir / "uploads"
        self.indexes_dir = self.base_dir / "indexes"
        self.reports_dir = Path("reports")

        for d in [self.uploads_dir, self.indexes_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_bytes: bytes, destination_path: str) -> str:
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file_bytes)
        logger.info(f"Saved {len(file_bytes)} bytes to local file: {dest}")
        return str(dest.resolve())

    def get_file(self, path_or_uri: str) -> bytes:
        p = Path(path_or_uri)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path_or_uri}")
        return p.read_bytes()

    def delete_file(self, path_or_uri: str) -> bool:
        p = Path(path_or_uri)
        if p.exists():
            p.unlink()
            return True
        return False

    def list_files(self, prefix: str = "") -> List[str]:
        p = Path(prefix) if prefix else self.base_dir
        if not p.exists():
            return []
        return [str(f.resolve()) for f in p.rglob("*") if f.is_file()]

    def cleanup_old_files(self, max_age_hours: int = 48) -> int:
        """Deletes files older than max_age_hours in upload and temp directories."""
        now = datetime.now().timestamp()
        cutoff = now - (max_age_hours * 3600)
        deleted_count = 0

        for folder in [self.uploads_dir]:
            for item in folder.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    if item.stat().st_mtime < cutoff:
                        try:
                            item.unlink()
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Could not delete {item}: {e}")
        return deleted_count


class S3StorageAdapter(StorageAdapter):
    """
    AWS S3 Storage Adapter for scalable cloud production deployment.
    Requires AWS credentials in environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET).
    Gracefully falls back to LocalStorageAdapter if boto3 or credentials are unavailable.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or os.getenv("AWS_S3_BUCKET", "fin-sight-ai-storage")
        self._s3_client = None
        self._available = False

        try:
            import boto3
            self._s3_client = boto3.client("s3")
            self._available = True
            logger.info(f"S3StorageAdapter initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.info(f"boto3 / AWS S3 not configured ({e}). Cloud adapter in standby mode.")

    def is_available(self) -> bool:
        return self._available and self._s3_client is not None

    def save_file(self, file_bytes: bytes, destination_path: str) -> str:
        if not self.is_available():
            raise RuntimeError("S3 client is not available. Provide AWS credentials.")
        clean_key = destination_path.replace("\\", "/").lstrip("/")
        self._s3_client.put_object(Bucket=self.bucket_name, Key=clean_key, Body=file_bytes)
        return f"s3://{self.bucket_name}/{clean_key}"

    def get_file(self, path_or_uri: str) -> bytes:
        if not self.is_available():
            raise RuntimeError("S3 client is not available.")
        key = path_or_uri.replace(f"s3://{self.bucket_name}/", "").replace("\\", "/")
        response = self._s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    def delete_file(self, path_or_uri: str) -> bool:
        if not self.is_available():
            return False
        key = path_or_uri.replace(f"s3://{self.bucket_name}/", "").replace("\\", "/")
        self._s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        return True

    def list_files(self, prefix: str = "") -> List[str]:
        if not self.is_available():
            return []
        resp = self._s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        return [f"s3://{self.bucket_name}/{item['Key']}" for item in resp.get("Contents", [])]

    def cleanup_old_files(self, max_age_hours: int = 48) -> int:
        return 0


# Factory helper
def get_storage_adapter() -> StorageAdapter:
    """Returns S3 adapter if AWS_S3_BUCKET is explicitly configured and available, else local adapter."""
    if os.getenv("AWS_S3_BUCKET"):
        s3 = S3StorageAdapter()
        if s3.is_available():
            return s3
    return LocalStorageAdapter()
