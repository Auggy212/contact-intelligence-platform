from typing import Protocol, runtime_checkable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class StorageClient(Protocol):
    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload bytes to storage. Returns the storage key."""
        ...

    async def download(self, key: str) -> bytes:
        """Download bytes from storage by key."""
        ...

    async def presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        """Generate a time-limited presigned download URL."""
        ...

    async def delete(self, key: str) -> None:
        """Delete an object from storage."""
        ...


class MinIOStorageClient:
    """Local dev storage using MinIO (S3-compatible)."""

    def __init__(self) -> None:
        from minio import Minio
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info("minio_bucket_created", bucket=self._bucket)

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        import io
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.debug("minio_upload", key=key, bytes=len(data))
        return key

    async def download(self, key: str) -> bytes:
        response = self._client.get_object(bucket_name=self._bucket, object_name=key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        from datetime import timedelta
        return self._client.presigned_get_object(
            bucket_name=self._bucket,
            object_name=key,
            expires=timedelta(seconds=expires_seconds),
        )

    async def delete(self, key: str) -> None:
        self._client.remove_object(bucket_name=self._bucket, object_name=key)


class S3StorageClient:
    """Production storage using AWS S3."""

    def __init__(self) -> None:
        import boto3
        self._client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self._bucket = settings.S3_BUCKET

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        import io
        self._client.upload_fileobj(
            io.BytesIO(data),
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    async def download(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

    async def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


def get_storage_client() -> StorageClient:
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageClient()
    return MinIOStorageClient()
