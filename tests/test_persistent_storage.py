import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from persistent_storage import PersistentObjectStorage, STORAGE_ENV_VARS


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
        environment = {name: "" for name in STORAGE_ENV_VARS}
        environment[STORAGE_ENV_VARS[0]] = "bucket"
        with patch.dict(os.environ, environment, clear=False):
            with self.assertRaisesRegex(RuntimeError, "partially configured"):
                PersistentObjectStorage.from_environment()

    def test_storage_is_optional_when_no_configuration_is_present(self):
        with patch.dict(os.environ, {name: "" for name in STORAGE_ENV_VARS}, clear=False):
            self.assertIsNone(PersistentObjectStorage.from_environment())


if __name__ == "__main__":
    unittest.main()
