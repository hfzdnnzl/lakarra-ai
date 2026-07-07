"""Object storage abstraction (AWS S3 compatible).

Business logic depends only on :class:`StorageService`, never on the AWS SDK. The
``local`` backend (default) writes to the filesystem for development; the ``s3``
backend uses AWS S3 (or any S3-compatible endpoint) via boto3, imported lazily so
the dependency is only required when actually used.

This prepares future asset storage (images, video, exported documents). It is not
yet wired into content generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from ..config import get_settings


class StorageService(ABC):
    """Common interface for object storage backends."""

    @abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """Store bytes under ``key`` and return a reference (URL/URI)."""

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Return an accessible URL/URI for ``key``."""

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorageService(StorageService):
    """Filesystem-backed storage for local development."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._path(key)
        path.write_bytes(data)
        return path.as_uri()

    def get_url(self, key: str) -> str:
        return self._path(key).as_uri()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class S3StorageService(StorageService):
    """AWS S3 (or S3-compatible) backend. boto3 is imported lazily."""

    def __init__(
        self,
        bucket: str,
        *,
        region: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        self._client = None

    @property
    def client(self):  # pragma: no cover - requires AWS/boto3
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "s3", region_name=self.region, endpoint_url=self.endpoint_url
            )
        return self._client

    def put_object(  # pragma: no cover
        self, key: str, data: bytes, content_type: str | None = None
    ) -> str:
        extra = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)
        return self.get_url(key)

    def get_url(self, key: str) -> str:  # pragma: no cover
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket}/{key}"
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    def exists(self, key: str) -> bool:  # pragma: no cover
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def delete(self, key: str) -> None:  # pragma: no cover
        self.client.delete_object(Bucket=self.bucket, Key=key)


def build_storage_service() -> StorageService:
    settings = get_settings()
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET must be set when STORAGE_BACKEND=s3.")
        return S3StorageService(
            settings.s3_bucket,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
        )
    return LocalStorageService(settings.local_storage_dir)


@lru_cache
def get_storage() -> StorageService:
    """Return the process-wide storage service (cached singleton)."""

    return build_storage_service()
