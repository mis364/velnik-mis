import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from persistent_storage import S3_STORAGE_ENV_VARS, PersistentObjectStorage, from_environment


class FakePaginator:
    def __init__(self, client): self.client = client
    def paginate(self, Bucket, Prefix): return [{"Contents": [{"Key": key} for key in self.client.objects if key.startswith(Prefix)]}]


class FakeS3Client:
    def __init__(self, objects=None): self.objects = dict(objects or {})
    def get_paginator(self, operation_name): return FakePaginator(self)
    def download_file(self, bucket, key, filename): Path(filename).write_bytes(self.objects[key])
    def upload_file(self, filename, bucket, key, ExtraArgs=None): self.objects[key] = Path(filename).read_bytes()


class PersistentObjectStorageTests(unittest.TestCase):
    def make_storage(self, client): return PersistentObjectStorage(bucket="private-bucket", region="ap-southeast-2", client=client)

    def test_restores_remote_files_and_seeds_new_files(self):
        client = FakeS3Client({"velnik-mis/latest.xlsx": b"saved remote sales"})
        storage = self.make_storage(client)
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "latest.xlsx").write_bytes(b"stale local sales")
            (Path(directory) / "stock_latest.xlsx").write_bytes(b"initial stock")
            result = storage.sync_data_files(directory, ["latest.xlsx", "stock_latest.xlsx"])
            self.assertEqual((Path(directory) / "latest.xlsx").read_bytes(), b"saved remote sales")
            self.assertEqual(client.objects["velnik-mis/stock_latest.xlsx"], b"initial stock")
            self.assertEqual(result["restored"], ["latest.xlsx"])
            self.assertEqual(result["seeded"], ["stock_latest.xlsx"])

    def test_refuses_unsafe_file_names(self):
        storage = self.make_storage(FakeS3Client())
        with self.assertRaisesRegex(ValueError, "data filenames"):
            storage._key("..\\private.txt")

    def test_storage_is_optional_for_local_development(self):
        environment = {name: "" for name in S3_STORAGE_ENV_VARS}
        with patch.dict(os.environ, environment, clear=True): self.assertIsNone(from_environment())

    def test_amazon_s3_uses_task_iam_role(self):
        environment = {"SALES_MIS_STORAGE_PROVIDER": "s3", "SALES_MIS_STORAGE_BUCKET": "private-bucket", "SALES_MIS_STORAGE_REGION": "ap-southeast-2"}
        with patch.dict(os.environ, environment, clear=True):
            with patch("persistent_storage.PersistentObjectStorage") as storage_class: from_environment()
        storage_class.assert_called_once_with(bucket="private-bucket", region="ap-southeast-2", prefix="velnik-mis/")

    def test_amazon_s3_requires_bucket(self):
        with patch.dict(os.environ, {"SALES_MIS_STORAGE_PROVIDER": "s3"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SALES_MIS_STORAGE_BUCKET"): from_environment()

    def test_rejects_unsupported_provider(self):
        with patch.dict(os.environ, {"SALES_MIS_STORAGE_PROVIDER": "google_drive"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "must be s3"): from_environment()

    def test_rejects_static_credentials(self):
        environment = {"SALES_MIS_STORAGE_PROVIDER": "s3", "SALES_MIS_STORAGE_BUCKET": "private-bucket", "SALES_MIS_STORAGE_ACCESS_KEY_ID": "static-key"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "task IAM role"): from_environment()


if __name__ == "__main__": unittest.main()