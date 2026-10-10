import base64
import io
import json
import re
import tempfile
import time
import unittest
from collections import deque
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import app


class RealtimeTests(unittest.TestCase):
    def setUp(self):
        self.saved = None
        with app._realtime_lock:
            self.saved = dict(app._realtime)
            app._realtime.update(state="waiting", last_event_at=None, last_transport_sequence=None, gaps_since_start=0, pending={})

    def tearDown(self):
        with app._realtime_lock:
            app._realtime.clear()
            app._realtime.update(self.saved)

    @staticmethod
    def frames(code, sequence):
        body = b"\x00" * 32 + code + (b"\x00" * 8 if code in (b"A", b"R") else b"")
        return [b"sequence", body, sequence.to_bytes(4, "little")]

    def test_sequence_counts_blocks_mempool_and_gaps(self):
        now = int(time.time())
        self.assertEqual(app.process_zmq_frames(self.frames(b"C", 0xffffffff), now), ("block_connected", False))
        self.assertEqual(app.process_zmq_frames(self.frames(b"A", 0), now), ("mempool_added", False))
        self.assertEqual(app.process_zmq_frames(self.frames(b"R", 2), now), ("mempool_removed", True))
        self.assertEqual(app.process_zmq_frames(self.frames(b"D", 3), now), ("block_disconnected", False))
        with app._realtime_lock:
            counts = app._realtime["pending"][now - now % 60]
            self.assertEqual(tuple(counts[key] for key in app._ZMQ_COUNTERS), (1, 1, 1, 1, 1))

    def test_bad_frames_do_not_change_counters(self):
        for frames in ([b"other", b"\x00" * 33, b"\x00" * 4], [b"sequence", b"short", b"\x00" * 4], [b"sequence", b"\x00" * 33, b"bad"]):
            with self.assertRaises(ValueError):
                app.process_zmq_frames(frames)
        with app._realtime_lock:
            self.assertEqual(app._realtime["pending"], {})

    def test_sqlite_flush_and_live_summary(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATABASE_PATH", str(Path(directory) / "history.sqlite3")):
            app.init_database()
            app.process_zmq_frames(self.frames(b"A", 1))
            app.flush_zmq_counts()
            self.assertEqual(app.realtime_data()["counts"]["mempool_added"], 1)
            with closing(app.database_connection()) as connection:
                self.assertEqual(connection.execute("SELECT SUM(mempool_added) FROM zmq_events").fetchone()[0], 1)


class DashboardLayoutTests(unittest.TestCase):
    def test_tabs_keep_overview_short_and_details_available(self):
        html = (app.APP_DIR / "static" / "index.html").read_text(encoding="utf-8")
        panels = {}
        for name in ("overview", "network", "analysis", "history", "system"):
            match = re.search(rf'<section\b[^>]*id="{name}Panel"[^>]*>.*?</section>', html, re.S)
            self.assertIsNotNone(match, name)
            panels[name] = match.group(0)
            self.assertIn(f'id="tab-{name}"', html)
            self.assertIn(f'aria-controls="{name}Panel"', html)
        for name, ids in {
            "overview": ("blocks", "syncText", "version", "overviewPeers", "overviewAlerts"),
            "network": ("peers", "ipv4Peers", "ipv6Peers", "onionPeers", "peerQualityRows", "chainTipRows", "nodeIdentity", "externalStatus"),
            "analysis": ("mempoolTx", "fee2", "utxoCount", "feeBucketRows", "hash"),
            "history": ("peerChart", "feeChart", "systemChart", "diskChart", "timelineList"),
            "system": ("cpu", "memory", "disk", "versionStatus", "uptime"),
        }.items():
            for element_id in ids:
                self.assertIn(f'id="{element_id}"', panels[name])
        self.assertNotIn('id="peerQualityRows"', panels["overview"])
        self.assertNotIn('id="feeBucketRows"', panels["overview"])
        html_ids = re.findall(r'\bid="([^"]+)"', html)
        self.assertEqual(len(html_ids), len(set(html_ids)))
        self.assertIn('panel.hidden=!selected', html)
        self.assertIn('requestAnimationFrame(()=>{renderHistory();renderAnalytics()})', html)
        self.assertNotRegex(html, r"\b(rein|raus|Inbound|Outbound)\b")
        self.assertIn(" in · ", html)
        self.assertIn(" out", html)
        self.assertIn("Im externen Verzeichnis nicht erfasst", html)
        for element_id in ("chainTipsStatus", "activeTipHeight", "otherTipCount", "disconnectedBlocks"):
            self.assertIn(f'id="{element_id}"', panels["network"])


class ChainTipsTests(unittest.TestCase):
    def setUp(self):
        self.cache = dict(app._chain_tips_cache)

    def tearDown(self):
        app._chain_tips_cache.clear()
        app._chain_tips_cache.update(self.cache)

    def test_snapshot_counts_all_tips_but_limits_display(self):
        block_hash = "a" * 64
        raw = [{"height": 100, "branchlen": 0, "status": "active", "hash": block_hash}]
        raw += [{"height": height, "branchlen": 1, "status": "valid-fork", "hash": f"{height:064x}"} for height in range(80, 100)]
        raw += [{"height": 99, "branchlen": 1, "status": "valid-headers", "hash": "b" * 64}]
        raw += [{"height": 101, "branchlen": -1, "status": "invalid", "hash": "bad"}]
        result = app.summarize_chain_tips(raw, 123)
        self.assertEqual(result["active"]["height"], 100)
        self.assertEqual(result["other_count"], 21)
        self.assertEqual(result["status_counts"], {"valid-fork": 20, "valid-headers": 1})
        self.assertEqual(len(result["other_tips"]), 12)
        self.assertEqual(result["other_tips"][0]["height"], 99)
        self.assertFalse(app.summarize_chain_tips(None, 123)["available"])
        self.assertFalse(app.summarize_chain_tips(raw[1:], 123)["available"])

    def test_disconnect_count_uses_selected_range_and_rpc_cache(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATABASE_PATH", str(Path(directory) / "history.sqlite3")):
            app.init_database()
            app.record_event("block_disconnected", "Block getrennt", 9_000)
            app.record_event("block_disconnected", "Block getrennt", 19_000)
            raw = [{"height": 20, "branchlen": 0, "status": "active", "hash": "a" * 64}]
            with patch.object(app, "safe_call", return_value=raw) as rpc, patch.object(app.time, "time", return_value=20_000):
                hour = app.chain_tips_data("1h")
                day = app.chain_tips_data("24h")
            self.assertEqual(hour["disconnected_blocks"], 1)
            self.assertEqual(day["disconnected_blocks"], 2)
            self.assertEqual(day["last_disconnected_at"], 19_000)
            rpc.assert_called_once_with("getchaintips")


class ServiceConfigurationTests(unittest.TestCase):
    def test_state_env_is_used_by_service_bootstrap_and_release_fetcher(self):
        project = Path(__file__).parent.parent
        service = (project / "bitcoin-dashboard.service").read_text(encoding="utf-8")
        bootstrap = (project / "installer" / "bootstrap-admin.sh").read_text(encoding="utf-8")
        fetcher = (project / "installer" / "fetch-dashboard-release").read_text(encoding="utf-8")
        self.assertIn("EnvironmentFile=/var/lib/bitcoin-dashboard/.env", service)
        self.assertIn("legacy_env=/etc/default/bitcoin-dashboard", bootstrap)
        self.assertIn('ln -s "$env_file" "$dashboard_target/.env"', bootstrap)
        self.assertIn("--unit=bitcoin-dashboard-config-restart", bootstrap)
        self.assertIn('ENV_FILE = Path("/var/lib/bitcoin-dashboard/.env")', fetcher)

    def test_update_helpers_use_root_owned_cache_and_bootstrap_migrates_config(self):
        project = Path(__file__).parent.parent
        cache = "/var/cache/bitcoin-dashboard-updates"
        for helper in ("update-bitcoin-dashboard", "update-bitcoin-core"):
            script = (project / "installer" / helper).read_text(encoding="utf-8")
            self.assertIn(cache, script)
            self.assertIn('test "$(stat -c %u "$UPDATE_ROOT")" = 0', script)
            self.assertIn('test "$(stat -c %a "$UPDATE_ROOT")" = 700', script)
        bootstrap = (project / "installer" / "bootstrap-admin.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('install -d -o root -g root -m 0700 "$update_root"', bootstrap)
        self.assertIn('sed -i "s#^UPDATE_ROOT=.*#UPDATE_ROOT=$update_root#"', bootstrap)

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

    def test_updater_waits_for_service_health_after_restart(self):
        project = Path(__file__).parent.parent
        updater = (project / "installer" / "update-bitcoin-dashboard").read_text()

        self.assertIn('while test "$attempt" -lt 30', updater)
        self.assertIn("if ! wait_for_health; then", updater)
        self.assertIn('echo "Rollback healthcheck failed"', updater)

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

    def test_all_in_one_keeps_rpc_private_and_runs_without_root(self):
        compose = (app.APP_DIR / "compose.all-in-one.yaml").read_text(
            encoding="utf-8"
        )
        dockerfile = (app.APP_DIR / "Dockerfile.all-in-one").read_text(
            encoding="utf-8"
        )
        bitcoin_config = (
            app.APP_DIR / "docker" / "bitcoin-all-in-one.conf"
        ).read_text(encoding="utf-8")

        self.assertNotIn("8332:8332", compose)
        self.assertNotIn("docker.sock", compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("cap_drop:\n      - ALL", compose)
        self.assertIn("USER node:node", dockerfile)
        self.assertIn("rpcbind=127.0.0.1", bitcoin_config)
        self.assertIn("rpcallowip=127.0.0.1", bitcoin_config)

    def test_all_in_one_stops_both_child_processes(self):
        entrypoint = (
            app.APP_DIR / "docker" / "all-in-one-entrypoint.sh"
        ).read_text(encoding="utf-8")

        self.assertIn('trap shutdown_children TERM INT', entrypoint)
        self.assertIn('wait -n "$bitcoin_pid" "$dashboard_pid"', entrypoint)
        self.assertIn('bitcoin-cli -datadir="$BITCOIN_DATADIR" stop', entrypoint)

    def test_shell_installer_is_non_destructive_and_checks_ports(self):
        installer = (
            app.APP_DIR / "installer" / "install-docker-all-in-one.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("--prepare-only", installer)
        self.assertIn("Port 8333 or 8787 is already in use", installer)
        self.assertIn("Refusing symbolic link", installer)
        self.assertNotIn("systemctl stop", installer)
        self.assertNotIn("down -v", installer)

    def test_plesk_apache_template_contains_no_nginx_directives(self):
        configuration = (app.APP_DIR / "plesk-apache-docker.conf").read_text(
            encoding="utf-8"
        )

        self.assertIn("LimitRequestBody 209715200", configuration)
        self.assertIn("ProxyPass", configuration)
        self.assertNotIn("client_max_body_size", configuration)


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


class PeerNetworkTests(unittest.TestCase):
    def setUp(self):
        with app._peer_observation_lock:
            app._peer_observation.update(active=None, uptime=None, observed_at=None, departures=deque())

    def test_peer_quality_is_aggregated_without_addresses(self):
        peers = [
            {"id": 1, "addr": "192.0.2.1:8333", "network": "ipv4", "conntime": 900, "pingtime": 0.01, "version": 70016, "transport_protocol_type": "v2"},
            {"id": 2, "addr": "192.0.2.2:8333", "network": "ipv4", "conntime": 800, "pingtime": 0.03, "version": 70016, "transport_protocol_type": "v1"},
            {"id": 3, "network": "onion", "conntime": 950, "version": 70015},
        ]
        result = app.peer_quality_summary(peers, 1000, {"ipv4": 2})
        self.assertEqual(result["ipv4"], {
            "count": 2,
            "median_connection_seconds": 150,
            "median_ping_ms": 20.0,
            "protocol_version": 70016,
            "transport_v2": 1,
            "departures_1h": 2,
        })
        self.assertNotIn("192.0.2", json.dumps(result))
        self.assertIsNone(result["onion"]["median_ping_ms"])

    def test_departures_exclude_short_tests_and_reset_on_node_restart(self):
        stable = {"id": 1, "network": "ipv6", "conntime": 100, "connection_type": "inbound"}
        feeler = {"id": 2, "network": "ipv4", "conntime": 100, "connection_type": "feeler"}
        self.assertEqual(app.observe_peer_departures([stable, feeler], 100, 200), {})
        self.assertEqual(app.observe_peer_departures([], 160, 260), {"ipv6": 1})
        self.assertEqual(app.observe_peer_departures([], 161, 261), {"ipv6": 1})
        self.assertEqual(app.observe_peer_departures([], 2, 262), {})
        self.assertEqual(app.observe_peer_departures([], 4000, 4262), {})

    def test_departures_reset_after_restart_during_long_observation_gap(self):
        peer = {"id": 1, "network": "onion", "conntime": 100, "connection_type": "inbound"}
        app.observe_peer_departures([peer], 100, 200)
        self.assertEqual(app.observe_peer_departures([], 1000, 3800), {})

    def test_only_global_host_ipv6_is_displayed(self):
        interfaces = (
            "fe800000000000000001b0fffe81d201 02 40 20 80 ens6\n"
            "2a010239029bf9000000000000000001 02 80 00 80 ens6\n"
            "00000000000000000000000000000001 01 80 10 80 lo\n"
        )
        self.assertEqual(
            app.parse_global_ipv6_addresses(interfaces),
            ["2a01:239:29b:f900::1"],
        )

    def test_snapshot_separates_peer_networks_and_directions(self):
        replies = {
            "getblockchaininfo": {"blocks": 0},
            "getnetworkinfo": {
                "connections": 4,
                "localaddresses": [
                    {"address": "217.160.16.224", "port": 8333},
                    {"address": "217.160.16.224", "port": 8333},
                    {"address": "2001:db8::1", "port": 8333},
                    {"address": "not-an-ip", "port": 8333},
                    {"address": "exampleonion.onion", "port": 8333},
                ],
            },
            "getmempoolinfo": {},
            "getnettotals": {},
            "getpeerinfo": [
                {"network": "ipv4", "inbound": True},
                {"network": "ipv4", "inbound": False},
                {"network": "ipv6", "inbound": False},
                {"network": "onion", "inbound": True},
            ],
        }
        with (
            patch.object(app, "PUBLIC_NODE_ADDRESS", "217.160.16.224"),
            patch.object(app, "host_global_ipv6_addresses", return_value=["2a01:239:29b:f900::1"]),
            patch.object(app, "bitcoin_cli", side_effect=lambda command: replies[command]),
            patch.object(app, "safe_call", return_value=None),
            patch.object(app, "fetch_latest_core_version", return_value={}),
            patch.object(app, "fetch_external_node_status", return_value={}),
            patch.object(app, "system_stats", return_value={}),
            patch.object(app, "mempool_analysis", return_value={}),
        ):
            network = app.build_snapshot()["network"]

        self.assertEqual(network["network_directions"]["ipv4"], {"inbound": 1, "outbound": 1})
        self.assertEqual(network["network_directions"]["ipv6"], {"inbound": 0, "outbound": 1})
        self.assertEqual(network["network_directions"]["onion"], {"inbound": 1, "outbound": 0})
        self.assertEqual(network["local_addresses"], {
            "ipv4": ["217.160.16.224"],
            "ipv6": ["2001:db8::1"],
            "onion": ["exampleonion.onion"],
        })
        self.assertEqual(network["onion_address"], "exampleonion.onion")
        self.assertEqual(network["configured_public_address"], {
            "family": "ipv4", "address": "217.160.16.224"
        })
        self.assertEqual(network["host_ipv6_addresses"], ["2a01:239:29b:f900::1"])


class MempoolAnalysisTests(unittest.TestCase):
    def test_summarizes_clusters_cpfp_rbf_and_standalone_transactions(self):
        entries = {
            "parent": {"depends": [], "spentby": ["child"], "bip125-replaceable": False, "vsize": 100, "fees": {"base": 0.000001}},
            "child": {"depends": ["parent"], "spentby": [], "bip125-replaceable": True, "vsize": 100, "fees": {"base": 0.00001}},
            "single": {"depends": [], "spentby": [], "bip125-replaceable": False, "vsize": 100, "fees": {"base": 0.000001}},
        }

        result = app.summarize_mempool(entries)

        self.assertTrue(result["available"])
        self.assertEqual(result["transactions"], 3)
        self.assertEqual(result["clusters"], 1)
        self.assertEqual(result["package_transactions"], 2)
        self.assertEqual(result["cpfp_transactions"], 1)
        self.assertEqual(result["rbf_transactions"], 1)
        self.assertEqual(result["rbf_replaceable_transactions"], 1)
        self.assertEqual(result["standalone_transactions"], 1)
        self.assertEqual(sum(bucket["transactions"] for bucket in result["fee_buckets"]), 3)
        self.assertEqual(result["classified_vbytes"], 300)

    def test_fee_buckets_are_non_overlapping_and_count_unknown_entries(self):
        rates = [0.5, 1, 2, 5, 10, 20, 50]
        entries = {
            str(index): {"vsize": 100 + index, "fees": {"base": rate * (100 + index) / 100_000_000}}
            for index, rate in enumerate(rates)
        }
        entries["unknown"] = {"vsize": 100, "fees": {}}
        result = app.summarize_mempool(entries)
        self.assertEqual([bucket["transactions"] for bucket in result["fee_buckets"]], [1] * 7)
        self.assertEqual([bucket["vbytes"] for bucket in result["fee_buckets"]], list(range(100, 107)))
        self.assertEqual(result["classified_vbytes"], sum(range(100, 107)))
        self.assertEqual(result["unclassified_transactions"], 1)

    def test_fee_buckets_unavailable_when_rpc_fails(self):
        result = app.summarize_mempool(None)
        self.assertFalse(result["available"])
        self.assertEqual(len(result["fee_buckets"]), 7)


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

    def test_node_missing_from_crawler_is_unknown_not_down(self):
        payload = {"found": False, "status": "DOWN", "data": None}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = app.fetch_external_node_status()
        self.assertTrue(result["available"])
        self.assertFalse(result["found"])
        self.assertIsNone(result["reachable"])
        with patch.object(app, "set_alert_condition") as alert:
            app.evaluate_alerts({"external_node": result})
        external_call = next(call for call in alert.call_args_list if call.args[0] == "external_unreachable")
        self.assertFalse(external_call.args[1])

    def test_listed_node_can_be_up_or_down(self):
        for status, expected in (("UP", True), ("DOWN", False), ("UNKNOWN", None)):
            with self.subTest(status=status):
                app._external_cache.update(expires=0.0, data=None)
                payload = {"found": True, "status": status, "data": []}
                with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
                    result = app.fetch_external_node_status()
                self.assertIs(result["reachable"], expected)


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

    def test_config_masks_secret_and_preserves_protected_values(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".env"
            config.write_text("ADMIN_TOKEN=" + "a" * 32 + "\nDASHBOARD_GITHUB_TOKEN=github_pat_secret\nBITCOIN_COOKIE=/secret/cookie\nDISK_MAX_USED_PERCENT=90\n", encoding="utf-8")
            with patch.object(app, "CONFIG_FILE", config), patch.object(app, "ADMIN_UPDATES_ENABLED", True):
                data = app.admin_config_data()
                fields = {field["key"]: field for field in data["fields"]}
                self.assertEqual(fields["DASHBOARD_GITHUB_TOKEN"]["value"], "")
                self.assertTrue(fields["DASHBOARD_GITHUB_TOKEN"]["configured"])
                self.assertNotIn("ADMIN_TOKEN", fields)
                proposed = {key: field["value"] for key, field in fields.items()}
                proposed["DISK_MAX_USED_PERCENT"] = "92.5"
                completed = type("Completed", (), {"returncode": 0})()
                with patch.object(app.subprocess, "run", return_value=completed) as run:
                    status, _ = app.save_admin_config(proposed)
                self.assertEqual(status, 202)
                self.assertEqual(run.call_args.args[0], app.ADMIN_CONFIG_RESTART_COMMAND)
                result = config.read_text(encoding="utf-8")
                self.assertIn("ADMIN_TOKEN=" + "a" * 32, result)
                self.assertIn("DASHBOARD_GITHUB_TOKEN=github_pat_secret", result)
                self.assertIn("BITCOIN_COOKIE=/secret/cookie", result)
                self.assertIn("DISK_MAX_USED_PERCENT=92.5", result)

    def test_config_rejects_injection_and_rolls_back_failed_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".env"
            original = "ADMIN_TOKEN=" + "a" * 32 + "\nDISK_MAX_USED_PERCENT=90\n"
            config.write_text(original, encoding="utf-8")
            with patch.object(app, "CONFIG_FILE", config), patch.object(app, "ADMIN_UPDATES_ENABLED", True):
                proposed = {field["key"]: field["value"] for field in app.admin_config_data()["fields"]}
                proposed["ALERT_WEBHOOK_URL"] = "https://example.org/hook\nADMIN_TOKEN=bad"
                with patch.object(app.subprocess, "run") as run:
                    status, _ = app.save_admin_config(proposed)
                self.assertEqual(status, 400)
                run.assert_not_called()
                proposed["ALERT_WEBHOOK_URL"] = ""
                proposed["DISK_MAX_USED_PERCENT"] = "95"
                failed = type("Completed", (), {"returncode": 1})()
                with patch.object(app.subprocess, "run", return_value=failed):
                    status, _ = app.save_admin_config(proposed)
                self.assertEqual(status, 503)
                self.assertEqual(config.read_text(encoding="utf-8"), original)

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

    def test_update_logs_use_only_fixed_journal_units(self):
        completed = type("Completed", (), {"returncode": 0, "stdout": "done\n", "stderr": ""})()
        with patch.object(app.subprocess, "run", return_value=completed) as run:
            status, message, state = app.admin_update_log("dashboard")
        self.assertEqual((status, message, state), (200, "done", "unknown"))
        self.assertEqual(run.call_args.args[0], app.ADMIN_LOG_COMMANDS["dashboard"])
        self.assertNotIn("shell", run.call_args.kwargs)
        with patch.object(app.subprocess, "run") as run:
            status, _, _ = app.admin_update_log("../../etc/passwd")
        self.assertEqual(status, 404)
        run.assert_not_called()

    def test_update_log_is_bounded_and_unavailable_in_container(self):
        completed = type("Completed", (), {"returncode": 0, "stdout": "x" * 40000, "stderr": ""})()
        with patch.object(app.subprocess, "run", return_value=completed):
            status, message, state = app.admin_update_log("bitcoin")
        self.assertEqual(status, 200)
        self.assertEqual(len(message), 32768)
        self.assertEqual(state, "unknown")
        with patch.object(app, "ADMIN_UPDATES_ENABLED", False):
            with patch.object(app.subprocess, "run") as run:
                status, _, _ = app.admin_update_log("bitcoin")
        self.assertEqual(status, 409)
        run.assert_not_called()

    def test_update_result_tracks_latest_systemd_run(self):
        unit = "bitcoin-dashboard-update.service"
        lines = [
            f"Sep 30 10:00:00 host systemd[1]: Started {unit} - updater.",
            f"Sep 30 10:00:01 host systemd[1]: {unit}: Deactivated successfully.",
            f"Sep 30 11:00:00 host systemd[1]: Started {unit} - updater.",
            "Sep 30 11:00:01 host updater[1]: Download läuft",
        ]
        state, output = app.update_result_from_journal("dashboard", "\n".join(lines))
        self.assertEqual(state, "running")
        self.assertNotIn("10:00:01", output)
        lines.append(f"Sep 30 11:00:02 host systemd[1]: {unit}: Failed with result 'exit-code'.")
        self.assertEqual(app.update_result_from_journal("dashboard", "\n".join(lines))[0], "failure")
        lines.append(f"Sep 30 12:00:00 host systemd[1]: Started {unit} - updater.")
        lines.append(f"Sep 30 12:00:01 host systemd[1]: {unit}: Deactivated successfully.")
        self.assertEqual(app.update_result_from_journal("dashboard", "\n".join(lines))[0], "success")


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
            "latest_block": {
                "txs": 2_000,
                "totalfee": 123_456,
                "total_size": 1_500_000,
                "transaction_rate": 3.25,
            },
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
        self.assertEqual(result["points"][0]["block_size_bytes"], 1_500_000.0)
        self.assertEqual(result["points"][0]["block_transaction_rate"], 3.25)

    def test_daily_utxo_sample_is_stored_once_per_interval(self):
        result = {
            "height": 900_000,
            "transactions": 100,
            "txouts": 200,
            "bogosize": 300,
            "disk_size": 400,
            "total_amount": 19_700_000.0,
        }
        old_attempt = app._utxo_last_attempt
        app._utxo_last_attempt = 0
        try:
            with patch.object(app, "bitcoin_cli", return_value=result) as rpc:
                self.assertTrue(app.store_daily_utxo_sample(100_000))
                self.assertFalse(app.store_daily_utxo_sample(100_100))
            rpc.assert_called_once_with("gettxoutsetinfo", "none", timeout=600)
            with closing(app.database_connection()) as connection:
                row = connection.execute(
                    "SELECT txouts FROM utxo_samples"
                ).fetchone()
            self.assertEqual(row["txouts"], 200)
        finally:
            app._utxo_last_attempt = old_attempt

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

    def test_timeline_filters_events_and_reports_known_gaps(self):
        app.record_event("dashboard_started", "Dashboard gestartet", 10_000)
        app.record_event("zmq_gap", "Sequenzlücke", 10_100)
        app.record_event("block_connected", "Neuer Block", 10_200)
        with patch.object(app.time, "time", return_value=10_300):
            result = app.timeline_data("1h")
        self.assertEqual([event["kind"] for event in result["events"]],
                         ["block_connected", "zmq_gap", "dashboard_started"])
        self.assertEqual(result["quality"]["zmq_gap"], 1)
        self.assertEqual(result["quality"]["dashboard_started"], 1)
        with patch.object(app.time, "time", return_value=20_000):
            self.assertEqual(app.timeline_data("1h")["events"], [])

    def test_node_restart_peer_drop_and_alert_transitions_are_recorded(self):
        first = self.sample(10_000, 20, 10, 8.0)
        second = self.sample(10_060, 10, 5, 8.0)
        second["network"]["bitcoind_uptime"] = 20
        app.store_snapshot(first)
        app.store_snapshot(second)
        with patch.object(app, "deliver_notification"):
            with patch.object(app.time, "time", return_value=10_100):
                app.set_alert_condition("test", True, "Fehler", 0)
            with patch.object(app.time, "time", return_value=10_101):
                app.set_alert_condition("test", True, "Fehler", 0)
            with patch.object(app.time, "time", return_value=10_102):
                app.set_alert_condition("test", False, "OK", 0)
        with patch.object(app.time, "time", return_value=10_200):
            kinds = [event["kind"] for event in app.timeline_data("1h")["events"]]
        self.assertEqual(kinds.count("node_restarted"), 1)
        self.assertEqual(kinds.count("peer_drop"), 1)
        self.assertEqual(kinds.count("alert_on"), 1)
        self.assertEqual(kinds.count("alert_off"), 1)

    def test_recent_blocks_are_backfilled_with_bounded_rpc_work(self):
        with closing(app.database_connection()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO block_observations VALUES (100, 4000, 4000, 10, 1000, 0.01, 1.0, 'snapshot')"
                )
        data = self.sample(5_000, 10, 5, 8.0)
        data["chain"]["blocks"] = 104
        data["latest_block"].update(time=4_240, txs=24, total_size=2_000)
        stats = lambda *args: {"time": 4000 + (int(args[1]) - 100) * 60,
                               "txs": 20, "total_size": 1800, "totalfee": 100000}
        with patch.object(app, "safe_call", side_effect=stats) as rpc:
            with patch.object(app.time, "time", return_value=5_000):
                app.backfill_missing_blocks(data, max_blocks=12)
                timeline = app.timeline_data("1h")
                with patch.object(app, "mempool_analysis", return_value={}):
                    analytics = app.analytics_data("1h")
        self.assertEqual(rpc.call_count, 3)
        self.assertEqual(timeline["quality"]["blocks_backfilled"], 3)
        self.assertEqual(timeline["quality"]["block_gap"], 0)
        self.assertTrue(any(point["block_size_bytes"] is not None for point in analytics["block_points"]))

    def test_sparse_block_observation_preserves_known_snapshot_rate(self):
        data = self.sample(5_000, 10, 5, 8.0)
        app.store_snapshot(data)
        with closing(app.database_connection()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO block_observations VALUES (100, 5000, 5000, 20, 2000, 0.01, NULL, 'rpc_backfill')"
                )
        with patch.object(app.time, "time", return_value=5_000):
            with patch.object(app, "mempool_analysis", return_value={}):
                points = app.analytics_data("1h")["block_points"]
        self.assertEqual(points[0]["block_transaction_rate"], 3.25)

    def test_failed_rpc_block_is_retried_on_next_sample(self):
        with closing(app.database_connection()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO block_observations VALUES (100, 4000, 4000, 10, 1000, 0.01, 1.0, 'snapshot')"
                )
        data = self.sample(5_000, 10, 5, 8.0)
        data["chain"]["blocks"] = 102
        data["latest_block"].update(time=4_120)
        with patch.object(app.time, "time", return_value=5_000):
            with patch.object(app, "safe_call", return_value=None):
                app.backfill_missing_blocks(data)
            with patch.object(app, "safe_call", return_value={
                "time": 4_060, "txs": 20, "total_size": 1800, "totalfee": 100000,
            }) as rpc:
                app.backfill_missing_blocks(data)
        rpc.assert_called_once_with("getblockstats", "101")
        with closing(app.database_connection()) as connection:
            row = connection.execute(
                "SELECT source FROM block_observations WHERE height = 101"
            ).fetchone()
        self.assertEqual(row["source"], "rpc_backfill")

    def test_large_block_gap_is_bounded_and_explicit(self):
        with closing(app.database_connection()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO block_observations VALUES (100, 4000, 4000, 10, 1000, 0.01, 1.0, 'snapshot')"
                )
        data = self.sample(5_000, 10, 5, 8.0)
        data["chain"]["blocks"] = 120
        data["latest_block"].update(time=5_200)
        with patch.object(app, "safe_call", return_value={"time": 5_100, "txs": 20, "total_size": 1000}) as rpc:
            with patch.object(app.time, "time", return_value=5_200):
                app.backfill_missing_blocks(data, max_blocks=3)
                timeline = app.timeline_data("1h")
        self.assertEqual(rpc.call_count, 2)
        self.assertEqual(timeline["quality"]["block_gap"], 1)
        self.assertIn("17 Blockstatistiken", next(event["message"] for event in timeline["events"] if event["kind"] == "block_gap"))


if __name__ == "__main__":
    unittest.main()
