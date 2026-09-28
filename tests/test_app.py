import tempfile
import unittest
from unittest.mock import patch

import app


class FeeRateTests(unittest.TestCase):
    def test_converts_btc_per_kvb_to_sat_per_vb(self):
        with patch.object(app, "safe_call", return_value={"feerate": 0.00001}):
            self.assertEqual(app.fee_rate(6), 1.0)

    def test_missing_estimate_returns_none(self):
        with patch.object(
            app,
            "safe_call",
            return_value={"errors": ["insufficient data"]},
        ):
            self.assertIsNone(app.fee_rate(2))


class ExternalStatusTests(unittest.TestCase):
    def setUp(self):
        app._external_cache.update(expires=0.0, data=None)

    def test_external_failure_is_non_fatal(self):
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            result = app.fetch_external_node_status()
        self.assertFalse(result["available"])
        self.assertIsNone(result["reachable"])
        self.assertEqual(result["address"], app.PUBLIC_NODE_ADDRESS)


class VersionTests(unittest.TestCase):
    def test_extracts_numeric_version(self):
        self.assertEqual(app.version_tuple("/Satoshi:32.0.1/"), (32, 0, 1))

    def test_invalid_version_is_empty(self):
        self.assertEqual(app.version_tuple("unknown"), ())


class HistoryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.old_database_path = app.DATABASE_PATH
        app.DATABASE_PATH = f"{self.temp_directory.name}/history.sqlite3"
        app.init_database()

    def tearDown(self):
        app.DATABASE_PATH = self.old_database_path
        self.temp_directory.cleanup()

    @staticmethod
    def sample(timestamp, connections, inbound, fee):
        return {
            "generated_at": timestamp,
            "chain": {
                "blocks": 900_000,
                "verification_progress": 1.0,
                "size_on_disk": 10_000,
            },
            "network": {
                "connections": connections,
                "connections_in": inbound,
                "connections_out": connections - inbound,
                "bytes_received": 100,
                "bytes_sent": 200,
                "bitcoind_uptime": 3_600,
            },
            "mempool": {
                "transactions": 10,
                "bytes": 2_000,
                "memory_usage": 3_000,
                "min_fee_btc_kvb": 0.00001,
            },
            "fees_sat_vb": {"2": fee, "6": fee / 2, "12": fee / 4},
            "latest_block": {"txs": 2_000, "totalfee": 123_456},
            "system": {
                "cpu_percent": 12.5,
                "memory": {"used_percent": 42.0},
                "disk": {"free_percent": 66.0, "free": 99_000},
            },
        }

    def test_stores_and_returns_bucketed_history(self):
        app.store_snapshot(self.sample(1_000, 20, 10, 8.0))
        app.store_snapshot(self.sample(1_400, 24, 12, 10.0))

        with patch.object(app.time, "time", return_value=1_500):
            result = app.history_data("24h")

        self.assertEqual(result["range"], "24h")
        self.assertEqual(len(result["points"]), 2)
        self.assertEqual(result["points"][0]["connections"], 20.0)
        self.assertEqual(result["points"][1]["fee_2_sat_vb"], 10.0)
        self.assertEqual(result["points"][0]["cpu_percent"], 12.5)
        self.assertEqual(result["points"][0]["disk_free_percent"], 66.0)

    def test_unknown_range_falls_back_to_24_hours(self):
        with patch.object(app.time, "time", return_value=1_500):
            result = app.history_data("invalid")
        self.assertEqual(result["range"], "24h")
        self.assertEqual(result["bucket_seconds"], 300)

    def test_one_hour_range_keeps_minute_buckets(self):
        with patch.object(app.time, "time", return_value=1_500):
            result = app.history_data("1h")
        self.assertEqual(result["range"], "1h")
        self.assertEqual(result["bucket_seconds"], 60)

    def test_alert_activates_after_grace_and_sends_recovery(self):
        with patch.object(app, "deliver_notification") as notify:
            with patch.object(app.time, "time", return_value=1_000):
                app.set_alert_condition("test", True, "Fehler", 300)
            self.assertEqual(app.active_alerts(), [])

            with patch.object(app.time, "time", return_value=1_301):
                app.set_alert_condition("test", True, "Fehler", 300)
            self.assertEqual(len(app.active_alerts()), 1)
            self.assertEqual(notify.call_count, 1)

            with patch.object(app.time, "time", return_value=1_400):
                app.set_alert_condition("test", False, "OK", 300)
            self.assertEqual(app.active_alerts(), [])
            self.assertEqual(notify.call_count, 2)


if __name__ == "__main__":
    unittest.main()
