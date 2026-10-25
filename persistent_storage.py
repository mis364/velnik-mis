from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config


R2_STORAGE_ENV_VARS = (
    "SALES_MIS_STORAGE_BUCKET",
    "SALES_MIS_STORAGE_ENDPOINT_URL",
    "SALES_MIS_STORAGE_ACCESS_KEY_ID",
    "SALES_MIS_STORAGE_SECRET_ACCESS_KEY",
)
DRIVE_STORAGE_ENV_VARS = (
    "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_DRIVE_FOLDER_ID",
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


class GoogleDriveStorage:
    def __init__(self, service_account_json, folder_id, service=None):
        self.folder_id = folder_id
        if service is None:
            import google.auth
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            if service_account_json:
                try:
                    service_account_info = json.loads(service_account_json)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON is not valid JSON."
                    ) from exc
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=["https://www.googleapis.com/auth/drive"],
                )
            else:
                credentials, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/drive"]
                )
            service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.service = service
        folder = self.service.files().get(
            fileId=folder_id,
            fields="id,mimeType,driveId",
            supportsAllDrives=True,
        ).execute()
        if folder.get("mimeType") != "application/vnd.google-apps.folder" or not folder.get("driveId"):
            raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID must identify a folder in a Shared Drive.")
        self.drive_id = folder["driveId"]

    @staticmethod
    def _safe_filename(filename):
        if Path(filename).name != filename:
            raise ValueError("Persistent storage only accepts data filenames.")
        return filename

    def _list_files(self):
        files = []
        page_token = None
        while True:
            result = self.service.files().list(
                q=f"'{self.folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name)",
                pageSize=1000,
                pageToken=page_token,
                corpora="drive",
                driveId=self.drive_id,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            files.extend(result.get("files", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                return files

    def _files_by_name(self):
        by_name = {}
        for item in self._list_files():
            name = item.get("name")
            if name in by_name:
                raise RuntimeError(
                    f"Google Drive folder contains multiple files named {name!r}; "
                    "remove duplicates before continuing."
                )
            by_name[name] = item["id"]
        return by_name

    def sync_data_files(self, data_dir, filenames):
        from googleapiclient.http import MediaIoBaseDownload

        filenames = set(filenames)
        remote_files = self._files_by_name()
        restored = sorted(filenames.intersection(remote_files))
        for filename in restored:
            self._safe_filename(filename)
            request = self.service.files().get_media(
                fileId=remote_files[filename],
                supportsAllDrives=True,
            )
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=data_dir,
                prefix=f".{filename}.",
                suffix=".downloading",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                downloader = MediaIoBaseDownload(temporary, request)
                complete = False
                while not complete:
                    _, complete = downloader.next_chunk()
                temporary.flush()
                os.fsync(temporary.fileno())
            try:
                temporary_path.replace(Path(data_dir) / filename)
            finally:
                temporary_path.unlink(missing_ok=True)

        seeded = []
        for filename in sorted(filenames - set(restored)):
            source = Path(data_dir) / filename
            if source.is_file():
                self.upload_file(source, filename)
                seeded.append(filename)
        return {"restored": restored, "seeded": seeded}

    def upload_file(self, local_path, filename=None):
        from googleapiclient.http import MediaFileUpload

        path = Path(local_path)
        name = self._safe_filename(filename or path.name)
        media = MediaFileUpload(str(path), resumable=True)
        existing_file_id = self._files_by_name().get(name)
        if existing_file_id:
            self.service.files().update(
                fileId=existing_file_id,
                media_body=media,
                supportsAllDrives=True,
            ).execute()
        else:
            self.service.files().create(
                body={"name": name, "parents": [self.folder_id]},
                media_body=media,
                supportsAllDrives=True,
                fields="id",
            ).execute()


def from_environment():
    provider = os.environ.get("SALES_MIS_STORAGE_PROVIDER", "").strip().lower()
    r2_values = {name: os.environ.get(name, "").strip() for name in R2_STORAGE_ENV_VARS}
    drive_values = {name: os.environ.get(name, "").strip() for name in DRIVE_STORAGE_ENV_VARS}
    r2_configured = any(r2_values.values())
    drive_configured = any(drive_values.values())

    if provider not in {"", "r2", "google_drive"}:
        raise RuntimeError("SALES_MIS_STORAGE_PROVIDER must be r2 or google_drive.")
    if provider == "r2" and drive_configured or provider == "google_drive" and r2_configured:
        raise RuntimeError("Configure only the selected persistent storage provider.")
    if provider == "r2" or not provider and r2_configured:
        configured = [bool(value) for value in r2_values.values()]
        if any(configured) and not all(configured):
            missing = [name for name, value in r2_values.items() if not value]
            raise RuntimeError(
                "External workbook storage is partially configured; set all of: "
                + ", ".join(missing)
            )
        if not any(configured):
            if provider == "r2":
                raise RuntimeError("Configure all SALES_MIS_STORAGE_* variables for R2.")
            return None
        return PersistentObjectStorage(
            bucket=r2_values["SALES_MIS_STORAGE_BUCKET"],
            endpoint_url=r2_values["SALES_MIS_STORAGE_ENDPOINT_URL"],
            access_key_id=r2_values["SALES_MIS_STORAGE_ACCESS_KEY_ID"],
            secret_access_key=r2_values["SALES_MIS_STORAGE_SECRET_ACCESS_KEY"],
            region=os.environ.get("SALES_MIS_STORAGE_REGION", "auto").strip() or "auto",
            prefix=os.environ.get("SALES_MIS_STORAGE_PREFIX", "velnik-mis/"),
        )

    if provider == "google_drive" or drive_configured:
        if not drive_values["GOOGLE_DRIVE_FOLDER_ID"]:
            raise RuntimeError("Set GOOGLE_DRIVE_FOLDER_ID for Google Drive storage.")
        return GoogleDriveStorage(
            service_account_json=drive_values["GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON"],
            folder_id=drive_values["GOOGLE_DRIVE_FOLDER_ID"],
        )
    return None
