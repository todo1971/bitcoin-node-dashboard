import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class ServiceConfigurationTests(unittest.TestCase):
    def test_dashboard_service_does_not_force_no_new_privileges(self):
        project = Path(__file__).parent.parent
        configurations = (
            (project / "bitcoin-dashboard.service").read_text(),
            (project / "installer" / "web_installer.py").read_text(),
        )
        incompatible = (
            "NoNewPrivileges=",
            "PrivateDevices=",
            "ProtectClock=",
            "ProtectKernelLogs=",
            "ProtectKernelModules=",
            "ProtectKernelTunables=",
            "RestrictNamespaces=",
            "LockPersonality=",
            "SystemCallArchitectures=",
        )
        for configuration in configurations:
            for directive in incompatible:
                self.assertNotIn(directive, configuration)

    def test_updater_allows_unprivileged_test_user_to_enter_temp_directory(self):
        project = Path(__file__).parent.parent
        updater = (project / "installer" / "update-bitcoin-dashboard").read_text()
        chmod_position = updater.index('chmod 0750 "$tmp_dir" "$source_dir"')
        runuser_position = updater.index('runuser -u "$DASHBOARD_USER"')
        self.assertLess(chmod_position, runuser_position)

    def test_updater_uses_a_writable_python_cache_for_unprivileged_tests(self):
        project = Path(__file__).parent.parent
        updater = (project / "installer" / "update-bitcoin-dashboard").read_text()
        cache_position = updater.index(
            'install -d -o "$DASHBOARD_USER" -g "$dashboard_group" -m 0700 "$pycache_dir"'
        )
        runuser_position = updater.index('runuser -u "$DASHBOARD_USER"')

        self.assertLess(cache_position, runuser_position)
        self.assertIn('PYTHONPYCACHEPREFIX="$pycache_dir"', updater)

    def test_core_updater_verifies_before_stopping_node(self):
        project = Path(__file__).parent.parent
        updater = (project / "installer" / "update-bitcoin-core").read_text()
        self.assertLess(updater.index("gpg --batch"), updater.index('systemctl stop "$BITCOIN_SERVICE"'))
        self.assertLess(updater.index('sha256sum "$archive"'), updater.index('systemctl stop "$BITCOIN_SERVICE"'))
        self.assertIn('release_url="https://bitcoincore.org/bin/bitcoin-core-$version"', updater)
        self.assertIn("Downgrade or reinstall rejected", updater)
        self.assertIn("BITCOIN_MIN_VALID_SIGNATURES:=2", updater)
        self.assertIn("valid_signatures", updater)
        self.assertGreater(
            updater.index("getblockchaininfo"),
            updater.index('systemctl start "$BITCOIN_SERVICE"'),
        )


class DockerConfigurationTests(unittest.TestCase):
    def test_full_stack_keeps_rpc_private_and_drops_privileges(self):
        compose = (app.APP_DIR / "compose.yaml").read_text(encoding="utf-8")

        self.assertNotIn("8332:8332", compose)
        self.assertNotIn("docker.sock", compose)
        self.assertIn('ADMIN_UPDATES_ENABLED: "0"', compose)
        self.assertIn("cap_drop:\n      - ALL", compose)
        self.assertIn("no-new-privileges:true", compose)

    def test_host_node_container_has_no_update_or_docker_access(self):
        compose = (app.APP_DIR / "compose.host-node.yaml").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("docker.sock", compose)
        self.assertNotIn("/run/systemd", compose)
        self.assertIn('ADMIN_UPDATES_ENABLED: "0"', compose)
        self.assertIn("BITCOIN_RPC_URL: http://127.0.0.1:8332", compose)

    def test_dashboard_image_runs_as_non_root_user(self):
        dockerfile = (app.APP_DIR / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("USER dashboard:dashboard", dockerfile)
        self.assertNotIn("sudo", dockerfile)


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


class JsonRpcTests(unittest.TestCase):
    def test_direct_rpc_uses_cookie_and_typed_parameters(self):
        payload = json.dumps({"result": {"feerate": 0.00001}, "error": None}).encode()

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        with tempfile.TemporaryDirectory() as directory:
            cookie = Path(directory) / ".cookie"
            cookie.write_text("__cookie__:secret")
            with patch.object(app, "BITCOIN_RPC_URL", "http://bitcoin-core:8332"):
                with patch.object(app, "BITCOIN_COOKIE", str(cookie)):
                    with patch("urllib.request.urlopen", return_value=Response(payload)) as call:
                        result = app.bitcoin_json_rpc("estimatesmartfee", "6")

        self.assertEqual(result["feerate"], 0.00001)
        request = call.call_args.args[0]
        sent = json.loads(request.data)
        self.assertEqual(sent["method"], "estimatesmartfee")
        self.assertEqual(sent["params"], [6])
        self.assertTrue(request.get_header("Authorization").startswith("Basic "))


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

    def test_github_release_reports_dashboard_update(self):
        payload = json.dumps(
            {
                "tag_name": "v9.8.7",
                "html_url": "https://github.com/example/project/releases/tag/v9.8.7",
            }
        ).encode()

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        app._dashboard_version_cache.update(expires=0.0, data=None)
        with patch.object(app, "DASHBOARD_GITHUB_REPOSITORY", "example/project"):
            with patch.object(app, "DASHBOARD_GITHUB_TOKEN", "secret-token"):
                with patch("urllib.request.urlopen", return_value=Response(payload)) as open_url:
                    result = app.fetch_latest_dashboard_version()

        self.assertTrue(result["available"])
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest"], "9.8.7")
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")

    def test_invalid_github_repository_is_not_requested(self):
        app._dashboard_version_cache.update(expires=0.0, data=None)
        with patch.object(app, "DASHBOARD_GITHUB_REPOSITORY", "https://evil.test/x"):
            with patch("urllib.request.urlopen") as open_url:
                result = app.fetch_latest_dashboard_version()
        self.assertFalse(result["available"])
        open_url.assert_not_called()


class AlertEvaluationTests(unittest.TestCase):
    def test_disk_alarm_fires_at_ninety_percent_used(self):
        data = {
            "chain": {"blocks": 100, "headers": 100},
            "network": {"connections_in": 1},
            "system": {
                "disk": {"free_percent": 10.0},
                "memory": {"used_percent": 50.0},
            },
            "external_node": {"available": False},
            "version_check": {"update_available": False},
        }
        with patch.object(app, "DISK_MAX_USED_PERCENT", 90.0):
            with patch.object(app, "set_alert_condition") as setter:
                app.evaluate_alerts(data)
        disk_call = next(
            call for call in setter.call_args_list if call.args[0] == "disk_space"
        )
        self.assertTrue(disk_call.args[1])
        self.assertIn("90.0%", disk_call.args[2])


class AdminSecurityTests(unittest.TestCase):
    def setUp(self):
        app._admin_failures.clear()
        app._admin_blocked_until = 0.0

    def test_valid_credentials_require_exact_username_and_token(self):
        token = "x" * 32
        encoded = base64.b64encode(f"admin:{token}".encode()).decode()
        with patch.object(app, "ADMIN_TOKEN", token):
            self.assertEqual(app.check_admin_auth(f"Basic {encoded}"), "ok")

    def test_five_wrong_passwords_lock_admin(self):
        token = "x" * 32
        encoded = base64.b64encode(b"admin:wrong").decode()
        with patch.object(app, "ADMIN_TOKEN", token):
            with patch.object(app.time, "monotonic", return_value=100.0):
                results = [
                    app.check_admin_auth(f"Basic {encoded}") for _ in range(5)
                ]
        self.assertEqual(results[-1], "locked")

    def test_non_ascii_credentials_fail_without_exception(self):
        token = "x" * 32
        encoded = base64.b64encode("admin:falschä".encode()).decode()
        with patch.object(app, "ADMIN_TOKEN", token):
            self.assertEqual(app.check_admin_auth(f"Basic {encoded}"), "failed")

    def test_cross_origin_post_is_rejected(self):
        headers = {
            "Host": "node.example.de",
            "Origin": "https://evil.example",
            "Sec-Fetch-Site": "cross-site",
        }
        self.assertFalse(app.admin_origin_allowed(headers))

    def test_update_command_has_no_user_controlled_arguments(self):
        completed = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(app.subprocess, "run", return_value=completed) as run:
            status, _ = app.start_admin_update("dashboard")
        self.assertEqual(status, 202)
        self.assertEqual(run.call_args.args[0], app.ADMIN_DASHBOARD_COMMAND)

    def test_container_mode_rejects_host_update_commands(self):
        with patch.object(app, "ADMIN_UPDATES_ENABLED", False):
            with patch.object(app.subprocess, "run") as run:
                status, message = app.start_admin_update("dashboard")
        self.assertEqual(status, 409)
        self.assertIn("extern", message)
        run.assert_not_called()


class BitcoinUploadTests(unittest.TestCase):
    def test_accepts_official_archive_name_for_matching_platform(self):
        self.assertEqual(
            app.parse_bitcoin_archive_name(
                "bitcoin-31.1-x86_64-linux-gnu.tar.gz"
            ),
            ("31.1", "x86_64-linux-gnu"),
        )

    def test_rejects_path_and_debug_archive_names(self):
        self.assertIsNone(
            app.parse_bitcoin_archive_name(
                "../bitcoin-31.1-x86_64-linux-gnu.tar.gz"
            )
        )
        self.assertIsNone(
            app.parse_bitcoin_archive_name(
                "bitcoin-31.1-x86_64-linux-gnu-debug.tar.gz"
            )
        )

    def test_streams_upload_to_fixed_staging_name(self):
        payload = b"\x1f\x8b" + b"release" * 100
        with tempfile.TemporaryDirectory() as directory:
            old_directory = app.BITCOIN_UPLOAD_DIR
            app.BITCOIN_UPLOAD_DIR = Path(directory)
            try:
                with patch.object(
                    app, "bitcoin_platform_name", return_value="x86_64-linux-gnu"
                ):
                    metadata = app.save_bitcoin_upload(
                        io.BytesIO(payload),
                        "bitcoin-31.1-x86_64-linux-gnu.tar.gz",
                        len(payload),
                    )
                self.assertEqual(metadata["version"], "31.1")
                self.assertEqual(
                    (Path(directory) / "bitcoin-core-upload.tar.gz").read_bytes(),
                    payload,
                )
                self.assertEqual(app.bitcoin_upload_status()["filename"], metadata["filename"])
            finally:
                app.BITCOIN_UPLOAD_DIR = old_directory

    def test_rejects_archive_for_other_platform(self):
        with patch.object(app, "bitcoin_platform_name", return_value="aarch64-linux-gnu"):
            with self.assertRaisesRegex(ValueError, "passt nicht"):
                app.save_bitcoin_upload(
                    io.BytesIO(b"\x1f\x8bpayload"),
                    "bitcoin-31.1-x86_64-linux-gnu.tar.gz",
                    9,
                )


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
        self.assertEqual(result["points"][0]["disk_used_percent"], 34.0)

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
