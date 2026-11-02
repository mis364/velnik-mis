from __future__ import annotations

import os
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config


S3_STORAGE_ENV_VARS = (
    "SALES_MIS_STORAGE_PROVIDER",
    "SALES_MIS_STORAGE_BUCKET",
    "SALES_MIS_STORAGE_REGION",
    "SALES_MIS_STORAGE_PREFIX",
)


class PersistentObjectStorage:
    def __init__(self, bucket, region="ap-southeast-2", prefix="velnik-mis/", client=None):
        self.bucket = bucket
        self.prefix = prefix.strip("/") + "/"
        self.client = client or boto3.client(
            "s3",
            region_name=region,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 5, "mode": "standard"},
                s3={"addressing_style": "path"},
            ),
        )

    def _key(self, filename):
        if not filename or Path(filename).name != filename:
            raise ValueError("Persistent storage only accepts data filenames.")
        return f"{self.prefix}{filename}"

    def sync_data_files(self, data_dir, filenames):
        """Restore known report files from S3 and seed files already present locally."""
        filenames = set(filenames)
        remote_files = set()
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for entry in page.get("Contents", []):
                key = entry["Key"]
                filename = key.removeprefix(self.prefix)
                if filename in filenames and key == self._key(filename):
                    remote_files.add(filename)

        data_dir = Path(data_dir)
        restored = []
        for filename in sorted(remote_files):
            destination = data_dir / filename
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=data_dir, prefix=f".{filename}.", suffix=".downloading", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
            try:
                self.client.download_file(self.bucket, self._key(filename), str(temporary_path))
                temporary_path.replace(destination)
                restored.append(filename)
            finally:
                temporary_path.unlink(missing_ok=True)

        seeded = []
        for filename in sorted(filenames - remote_files):
            source = data_dir / filename
            if source.is_file():
                self.upload_file(source, filename)
                seeded.append(filename)
        return {"restored": sorted(restored), "seeded": seeded}

    def upload_file(self, local_path, filename=None):
        path = Path(local_path)
        self.client.upload_file(
            str(path),
            self.bucket,
            self._key(filename or path.name),
            ExtraArgs={"ServerSideEncryption": "AES256"},
        )


def from_environment():
    provider = os.environ.get("SALES_MIS_STORAGE_PROVIDER", "").strip().lower()
    bucket = os.environ.get("SALES_MIS_STORAGE_BUCKET", "").strip()

    if provider and provider != "s3":
        raise RuntimeError("SALES_MIS_STORAGE_PROVIDER must be s3.")

    if not bucket:
        if provider == "s3":
            raise RuntimeError("Set SALES_MIS_STORAGE_BUCKET for Amazon S3 storage.")
        return None

    endpoint_names = (
        "SALES_MIS_STORAGE_ENDPOINT_URL",
        "SALES_MIS_STORAGE_ACCESS_KEY_ID",
        "SALES_MIS_STORAGE_SECRET_ACCESS_KEY",
    )
    configured = [name for name in endpoint_names if os.environ.get(name, "").strip()]
    if configured:
        raise RuntimeError(
            "Only the ECS task IAM role is supported for S3. Remove these unsupported provider variables: "
            + ", ".join(configured)
        )

    return PersistentObjectStorage(
        bucket=bucket,
        region=os.environ.get("SALES_MIS_STORAGE_REGION", "ap-southeast-2").strip()
        or "ap-southeast-2",
        prefix=os.environ.get("SALES_MIS_STORAGE_PREFIX", "velnik-mis/").strip()
        or "velnik-mis/",
    )