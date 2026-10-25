import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from persistent_storage import (
    DRIVE_STORAGE_ENV_VARS,
    R2_STORAGE_ENV_VARS,
    GoogleDriveStorage,
    PersistentObjectStorage,
    from_environment,
)


class FakePaginator:
    def __init__(self, client):
        self.client = client

    def paginate(self, Bucket, Prefix):
        keys = [
            {"Key": key}
            for key in self.client.objects
            if key.startswith(Prefix)
        ]
        return [{"Contents": keys}]


class FakeS3Client:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})

    def get_paginator(self, operation_name):
        if operation_name != "list_objects_v2":
            raise AssertionError(operation_name)
        return FakePaginator(self)

    def download_file(self, bucket, key, filename):
        Path(filename).write_bytes(self.objects[key])

    def upload_file(self, filename, bucket, key):
        self.objects[key] = Path(filename).read_bytes()


class FakeDriveRequest:
    def __init__(self, action):
        self.action = action

    def execute(self):
        return self.action()


class FakeDriveFiles:
    def __init__(self):
        self.files = {}
        self.created_parents = []
        self.updated_ids = []

    def list(self, **kwargs):
        return FakeDriveRequest(
            lambda: {
                "files": [
                    {"id": file_id, "name": name}
                    for file_id, name in self.files.items()
                ]
            }
        )

    def create(self, body, **kwargs):
        def create_file():
            file_id = f"file-{len(self.files) + 1}"
            self.files[file_id] = body["name"]
            self.created_parents.append(body["parents"])
            return {"id": file_id}

        return FakeDriveRequest(create_file)

    def update(self, fileId, **kwargs):
        return FakeDriveRequest(lambda: self.updated_ids.append(fileId))


class FakeDriveService:
    def __init__(self):
        self.file_resource = FakeDriveFiles()

    def files(self):
        return self.file_resource


class PersistentObjectStorageTests(unittest.TestCase):
    def make_storage(self, client):
        return PersistentObjectStorage(
            bucket="private-bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access-key",
            secret_access_key="secret-key",
            client=client,
        )

    def test_restores_remote_files_and_seeds_new_files(self):
        client = FakeS3Client({"velnik-mis/latest.xlsx": b"saved remote sales"})
        storage = self.make_storage(client)

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "latest.xlsx").write_bytes(b"stale local sales")
            (Path(directory) / "stock_latest.xlsx").write_bytes(b"initial stock")
            result = storage.sync_data_files(
                directory,
                ["latest.xlsx", "stock_latest.xlsx", "nepal_manual.json"],
            )

            self.assertEqual((Path(directory) / "latest.xlsx").read_bytes(), b"saved remote sales")
            self.assertEqual(
                client.objects["velnik-mis/stock_latest.xlsx"],
                b"initial stock",
            )
            self.assertEqual(result["restored"], ["latest.xlsx"])
            self.assertEqual(result["seeded"], ["stock_latest.xlsx"])

    def test_refuses_unsafe_file_names(self):
        storage = self.make_storage(FakeS3Client())
        with self.assertRaisesRegex(ValueError, "data filenames"):
            storage._key("..\\private.txt")

    def test_requires_all_storage_secrets_when_any_are_set(self):
        environment = {name: "" for name in R2_STORAGE_ENV_VARS}
        environment[R2_STORAGE_ENV_VARS[0]] = "bucket"
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "partially configured"):
                from_environment()

    def test_storage_is_optional_when_no_configuration_is_present(self):
        environment = {
            name: ""
            for name in (*R2_STORAGE_ENV_VARS, *DRIVE_STORAGE_ENV_VARS)
        }
        with patch.dict(os.environ, environment, clear=True):
            self.assertIsNone(from_environment())

    def test_google_drive_configuration_requires_both_variables(self):
        environment = {
            "SALES_MIS_STORAGE_PROVIDER": "google_drive",
            DRIVE_STORAGE_ENV_VARS[0]: "{}",
            DRIVE_STORAGE_ENV_VARS[1]: "",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GOOGLE_DRIVE_FOLDER_ID"):
                from_environment()

    def test_google_drive_provider_uses_configured_folder_and_service_account(self):
        environment = {
            "SALES_MIS_STORAGE_PROVIDER": "google_drive",
            DRIVE_STORAGE_ENV_VARS[0]: '{"type":"service_account"}',
            DRIVE_STORAGE_ENV_VARS[1]: "shared-folder-id",
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch("persistent_storage.GoogleDriveStorage") as storage_class:
                from_environment()

        storage_class.assert_called_once_with(
            service_account_json='{"type":"service_account"}',
            folder_id="shared-folder-id",
        )

    def test_google_drive_configuration_rejects_invalid_service_account_json(self):
        storage = GoogleDriveStorage.__new__(GoogleDriveStorage)
        with self.assertRaisesRegex(RuntimeError, "not valid JSON"):
            storage.__init__("not-json", "shared-folder-id")

    def test_google_drive_creates_new_file_in_configured_shared_folder(self):
        service = FakeDriveService()
        storage = GoogleDriveStorage(
            service_account_json="{}",
            folder_id="shared-folder-id",
            service=service,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest.xlsx"
            path.write_bytes(b"sales data")
            storage.upload_file(path)

        self.assertEqual(
            list(service.file_resource.files.values()),
            ["latest.xlsx"],
        )
        self.assertEqual(service.file_resource.created_parents, [["shared-folder-id"]])

    def test_google_drive_updates_existing_named_file(self):
        service = FakeDriveService()
        service.file_resource.files["existing-file"] = "latest.xlsx"
        storage = GoogleDriveStorage(
            service_account_json="{}",
            folder_id="shared-folder-id",
            service=service,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest.xlsx"
            path.write_bytes(b"new sales data")
            storage.upload_file(path)

        self.assertEqual(service.file_resource.updated_ids, ["existing-file"])


if __name__ == "__main__":
    unittest.main()
