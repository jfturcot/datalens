import io

from miniopy_async import Minio

from app.config import settings


def get_minio_client() -> Minio:
    """Create a MinIO async client from application settings."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_use_ssl,
    )


async def ensure_bucket(client: Minio, bucket: str) -> None:
    """Create the bucket if it does not already exist."""
    if not await client.bucket_exists(bucket):
        await client.make_bucket(bucket)


async def upload_file(
    session_id: str,
    filename: str,
    content: bytes,
) -> str:
    """Upload *content* to MinIO under ``uploads/{session_id}/{filename}``.

    Returns the object name (relative key).
    """
    client = get_minio_client()
    await ensure_bucket(client, settings.minio_bucket)

    object_name = f"{session_id}/{filename}"
    await client.put_object(
        settings.minio_bucket,
        object_name,
        io.BytesIO(content),
        length=len(content),
        content_type="text/csv",
    )
    return object_name
