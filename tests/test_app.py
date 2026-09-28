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


if __name__ == "__main__":
    unittest.main()
