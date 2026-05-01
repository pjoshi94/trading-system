import io

import boto3
import requests
from botocore.config import Config

from config import settings

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_from_url(source_url: str, filename: str) -> str:
    """Download PDF from source_url and upload to R2. Returns the stored URL."""
    resp = requests.get(
        source_url,
        headers={"User-Agent": _BROWSER_UA},
        timeout=60,
    )
    resp.raise_for_status()

    _s3().upload_fileobj(
        io.BytesIO(resp.content),
        settings.R2_BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": "application/pdf"},
    )

    return get_url(filename)


def get_url(filename: str) -> str:
    """Return the public URL for a stored file."""
    if settings.R2_PUBLIC_URL:
        base = settings.R2_PUBLIC_URL.rstrip("/")
        return f"{base}/{filename}"
    return f"r2://{settings.R2_BUCKET_NAME}/{filename}"


def file_exists(filename: str) -> bool:
    """Check whether a file already exists in the bucket."""
    try:
        _s3().head_object(Bucket=settings.R2_BUCKET_NAME, Key=filename)
        return True
    except Exception:
        return False
