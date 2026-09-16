import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import security


class FakeBackend:
    def __init__(self):
        self.synced = []
        self.deleted = []

    def sync_file(self, user_id, path, *, key=None):
        self.synced.append((user_id, path, key))

    def delete_files(self, user_id, paths):
        self.deleted.append((user_id, list(paths)))
        return len(paths)


class WorkspacePersistenceTests(unittest.TestCase):
    def test_persist_workspace_detects_deleted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deleted = root / "project_data" / "deleted.json"
            kept = root / "project_data" / "kept.json"
            deleted.parent.mkdir(parents=True)
            deleted.write_text("old", encoding="utf-8")
            kept.write_text("same", encoding="utf-8")
            before = security._workspace_snapshot(root)
            deleted.unlink()

            backend = FakeBackend()
            with patch.object(security, "get_storage_backend", return_value=backend):
                security._persist_workspace(root, root, before)

            self.assertEqual(backend.synced, [])
            self.assertEqual(len(backend.deleted), 1)
            self.assertEqual(backend.deleted[0][0], "local")
            self.assertEqual(backend.deleted[0][1], [deleted])


if __name__ == "__main__":
    unittest.main()
