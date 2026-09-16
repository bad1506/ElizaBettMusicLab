import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from storage_backend import S3StorageBackend


class FakeBody:
    def __init__(self, data: bytes):
        self.data = data

    def read(self):
        return self.data


class FakePaginator:
    def __init__(self, objects):
        self.objects = objects

    def paginate(self, **kwargs):
        yield {"Contents": self.objects}


class FakeS3:
    def __init__(self):
        self.objects = {}

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        objects = []
        for key, data in self.objects.items():
            objects.append({"Key": key, "ETag": '"etag-' + str(len(data)) + '"', "Size": len(data), "LastModified": datetime.now(timezone.utc)})
        return FakePaginator(objects)

    def get_object(self, **kwargs):
        return {"Body": FakeBody(self.objects[kwargs["Key"]])}

    def put_object(self, **kwargs):
        self.objects[kwargs["Key"]] = kwargs["Body"]

    def head_object(self, **kwargs):
        data = self.objects[kwargs["Key"]]
        return {"ETag": '"etag-' + str(len(data)) + '"', "ContentLength": len(data), "LastModified": datetime.now(timezone.utc)}


class S3StorageBackendTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "SONA_STORAGE_PROVIDER": "s3",
            "SONA_S3_BUCKET": "test-bucket",
            "SONA_S3_ACCESS_KEY_ID": "test-key",
            "SONA_S3_SECRET_ACCESS_KEY": "test-secret",
            "SONA_S3_HYDRATE_TTL": "0",
        }
        self.patcher = patch.dict(os.environ, self.env, clear=False)
        self.patcher.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.client = FakeS3()
        self.backend = S3StorageBackend(Path(self.tmp.name))
        self.client_patch = patch.object(self.backend, "_client", return_value=self.client)
        self.client_patch.start()

    def tearDown(self):
        self.client_patch.stop()
        self.patcher.stop()
        self.tmp.cleanup()

    def test_sync_file_uploads_only_workspace_file(self):
        root = self.backend.user_root("user-1")
        path = root / "project_data" / "project.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"hello")

        result = self.backend.sync_file("user-1", path)

        self.assertEqual(result.uploaded, 1)
        self.assertEqual(self.client.objects["sona/user_data/user-1/project_data/project.json"], b"hello")

    def test_hydrate_downloads_remote_object(self):
        key = "sona/user_data/user-1/mastering_input/track.wav"
        self.client.objects[key] = b"audio"

        result = self.backend.hydrate("user-1")

        path = self.backend.user_root("user-1") / "mastering_input" / "track.wav"
        self.assertEqual(result.downloaded, 1)
        self.assertEqual(path.read_bytes(), b"audio")

    def test_hydrate_preserves_newer_local_file(self):
        key = "sona/user_data/user-1/mastering_input/track.wav"
        self.client.objects[key] = b"remote"
        root = self.backend.user_root("user-1")
        path = root / "mastering_input" / "track.wav"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"local")
        meta = root / ".sona_storage_meta" / "mastering_input" / "track.wav.json"
        meta.parent.mkdir(parents=True)
        meta.write_text('{"etag":"old","size":1,"synced_at":"2000-01-01T00:00:00+00:00"}', encoding="utf-8")

        result = self.backend.hydrate("user-1")

        self.assertEqual(result.preserved_local, 1)
        self.assertEqual(path.read_bytes(), b"local")

    def test_sync_rejects_path_escape(self):
        root = self.backend.user_root("user-1")
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("x", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.backend.sync_file("user-1", outside)


if __name__ == "__main__":
    unittest.main()
