import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class BridgeContractTests(unittest.TestCase):
    def setUp(self):
        self.original_cache = dict(main.cache)
        main.cache.update(payload=None, mtime=None, read_error=None, last_sampled_at=None)

    def tearDown(self):
        main.cache.clear()
        main.cache.update(self.original_cache)

    def test_no_file_is_disconnected_and_execution_stays_disabled(self):
        state = main.snapshot_response()
        self.assertFalse(state["connected"])
        self.assertFalse(state["execution_enabled"])
        self.assertEqual(state["positions"], [])

    def test_valid_export_schema_is_read(self):
        payload = {
            "schema_version": 1,
            "generated_at_utc": "2026.11.15 10:00:00",
            "terminal": {"connected": True},
            "account": {
                "currency": "USD", "balance": 10000, "equity": 10020,
                "floating_pnl": 20, "margin": 100, "free_margin": 9920,
                "margin_level": 10020,
            },
            "positions": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir) / "GHOST"
            folder.mkdir()
            snapshot = folder / "telemetry.json"
            snapshot.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(main, "SNAPSHOT_PATH", snapshot):
                loaded, mtime, error = main.read_export()
        self.assertIsNone(error)
        self.assertIsNotNone(mtime)
        self.assertEqual(loaded["account"]["equity"], 10020)

    def test_stale_file_is_not_reported_as_connected(self):
        payload = {
            "terminal": {"connected": True},
            "account": {"equity": 10000},
            "positions": [],
        }
        main.cache.update(payload=payload, mtime=time.time() - main.STALE_AFTER_SECONDS - 2)
        state = main.snapshot_response()
        self.assertFalse(state["connected"])
        self.assertFalse(state["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
