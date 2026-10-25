from __future__ import annotations

import os
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config


STORAGE_ENV_VARS = (
    "SALES_MIS_STORAGE_BUCKET",
    "SALES_MIS_STORAGE_ENDPOINT_URL",
    "SALES_MIS_STORAGE_ACCESS_KEY_ID",
    "SALES_MIS_STORAGE_SECRET_ACCESS_KEY",
)


class PersistentObjectStorage:
    def __init__(
        self,
        bucket,
        endpoint_url,
        access_key_id,
        secret_access_key,
        region="auto",
        prefix="velnik-mis/",
        client=None,
    ):
        self.bucket = bucket
        self.prefix = prefix.strip("/") + "/"
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    @classmethod
    def from_environment(cls):
        values = {name: os.environ.get(name, "").strip() for name in STORAGE_ENV_VARS}
        configured = [bool(value) for value in values.values()]
        if any(configured) and not all(configured):
            missing = [name for name, value in values.items() if not value]
            raise RuntimeError(
                "External workbook storage is partially configured; set all of: "
                + ", ".join(missing)
            )
        if not any(configured):
            return None
        return cls(
            bucket=values["SALES_MIS_STORAGE_BUCKET"],
            endpoint_url=values["SALES_MIS_STORAGE_ENDPOINT_URL"],
            access_key_id=values["SALES_MIS_STORAGE_ACCESS_KEY_ID"],
            secret_access_key=values["SALES_MIS_STORAGE_SECRET_ACCESS_KEY"],
            region=os.environ.get("SALES_MIS_STORAGE_REGION", "auto").strip() or "auto",
            prefix=os.environ.get("SALES_MIS_STORAGE_PREFIX", "velnik-mis/"),
        )

    def _key(self, filename):
        if Path(filename).name != filename:
            raise ValueError("Persistent storage only accepts data filenames.")
        return f"{self.prefix}{filename}"

    def sync_data_files(self, data_dir, filenames):
        """Restore known report files from the bucket and seed missing objects."""
        filenames = set(filenames)
        remote_files = set()
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for entry in page.get("Contents", []):
                key = entry["Key"]
                filename = key.removeprefix(self.prefix)
                if filename in filenames and key == self._key(filename):
                    remote_files.add(filename)

        for filename in sorted(remote_files):
            destination = Path(data_dir) / filename
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=data_dir,
                prefix=f".{filename}.",
                suffix=".downloading",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            try:
                self.client.download_file(self.bucket, self._key(filename), str(temporary_path))
                temporary_path.replace(destination)
            finally:
                temporary_path.unlink(missing_ok=True)

        seeded = []
        for filename in sorted(filenames - remote_files):
            source = Path(data_dir) / filename
            if source.is_file():
                self.upload_file(source, filename)
                seeded.append(filename)
        return {"restored": sorted(remote_files), "seeded": seeded}

    def upload_file(self, local_path, filename=None):
        path = Path(local_path)
        self.client.upload_file(str(path), self.bucket, self._key(filename or path.name))
