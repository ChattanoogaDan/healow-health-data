import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from sync_store import detect_new_resources, read_cache, write_cache


class SyncStoreTests(unittest.TestCase):
    def test_first_sync_creates_baseline_without_new_alerts(self):
        old = {"resources": {}}
        current = {"resources": {"Observation": [{"id": "lab-1", "code": {"text": "Example"}}]}}
        self.assertEqual(detect_new_resources(old, current), {"first_sync": True, "new": []})

    def test_later_sync_reports_only_new_resource_ids(self):
        old = {"synced_at": "2026-10-18T12:00:00Z", "resources": {"Observation": [{"id": "lab-1"}]}}
        current = {"resources": {"Observation": [{"id": "lab-1"}, {"id": "lab-2"}]}}
        self.assertEqual(detect_new_resources(old, current), {"first_sync": False, "new": [{"resource_type": "Observation", "id": "lab-2"}]})

    def test_cache_round_trip_is_encrypted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.enc"
            key = Fernet.generate_key()
            payload = {"resources": {"Encounter": [{"id": "visit-1"}]}}
            write_cache(path, key, payload)
            self.assertNotIn(b"visit-1", path.read_bytes())
            self.assertEqual(read_cache(path, key), payload)


if __name__ == "__main__":
    unittest.main()
