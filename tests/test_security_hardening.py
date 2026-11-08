# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import base64
import importlib.util
import io
import json
import socket
import stat
import tarfile
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app

spec = importlib.util.spec_from_file_location("update_guard", app.APP_DIR/"installer/update_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class RootUpdateSecurityTests(unittest.TestCase):
    def test_archives_reject_links_traversal_and_duplicates_before_writing(self):
        for names, kind in ((["bitcoin-dashboard/a","bitcoin-dashboard/a"],tarfile.REGTYPE),
                            (["bitcoin-dashboard/../../escaped"],tarfile.REGTYPE),
                            (["/escaped"],tarfile.REGTYPE),
                            (["bitcoin-dashboard/link"],tarfile.SYMTYPE),
                            (["bitcoin-dashboard/link"],tarfile.LNKTYPE),
                            (["bitcoin-dashboard/device"],tarfile.FIFOTYPE)):
            with self.subTest(names=names,kind=kind), tempfile.TemporaryDirectory() as root:
                archive, destination = Path(root)/"test.tar.gz", Path(root)/"out"
                destination.mkdir()
                with tarfile.open(archive,"w:gz") as tar:
                    for name in names:
                        info=tarfile.TarInfo(name)
                        info.type=kind
                        info.linkname="/etc/passwd"
                        tar.addfile(info,io.BytesIO())
                with patch.object(guard,"trusted_path"), self.assertRaises(ValueError):
                    guard.extract_archive(archive,destination,"bitcoin-dashboard",100)
                self.assertEqual(list(destination.iterdir()),[])

    def test_archive_size_limit_and_version_read_never_execute_code(self):
        with tempfile.TemporaryDirectory() as root:
            marker=Path(root)/"executed"
            source=Path(root)/"app.py"
            source.write_text('__version__ = "1.2.3"\nraise RuntimeError("must not import")\n',encoding="utf-8")
            self.assertEqual(guard.release_version(source),"1.2.3")
            self.assertFalse(marker.exists())
            archive, destination=Path(root)/"a.tar.gz",Path(root)/"out"
            destination.mkdir()
            with tarfile.open(archive,"w:gz") as tar:
                info=tarfile.TarInfo("bitcoin-dashboard/a")
                info.size=2
                tar.addfile(info,io.BytesIO(b"ab"))
            with patch.object(guard,"trusted_path"),self.assertRaises(ValueError):
                guard.extract_archive(archive,destination,"bitcoin-dashboard",1)
            self.assertEqual(list(destination.iterdir()),[])

    def test_root_paths_reject_writable_ancestors_and_links(self):
        good=SimpleNamespace(st_uid=0,st_mode=stat.S_IFDIR|0o755)
        for bad in (SimpleNamespace(st_uid=1000,st_mode=stat.S_IFDIR|0o755),
                    SimpleNamespace(st_uid=0,st_mode=stat.S_IFDIR|0o775),
                    SimpleNamespace(st_uid=0,st_mode=stat.S_IFLNK|0o777)):
            with patch.object(Path,"lstat",side_effect=[good,bad]),self.assertRaises(ValueError):
                guard.trusted_path(Path("/opt/dashboard"))


class RequestSecurityTests(unittest.TestCase):
    def setUp(self):
        app._admin_failures.clear()
        app._admin_blocked_until.clear()
        app._request_limits.clear()

    def test_admin_failure_from_one_client_does_not_lock_another(self):
        with patch.object(app,"ADMIN_TOKEN","x"*32):
            for _ in range(5):
                result=app.check_admin_auth("Basic "+base64.b64encode(b"admin:wrong").decode(),"192.0.2.1")
            self.assertEqual(result,"locked")
            header="Basic "+base64.b64encode(("admin:"+"x"*32).encode()).decode()
            self.assertEqual(app.check_admin_auth(header,"192.0.2.2"),"ok")
            self.assertEqual(app.check_admin_auth(header,"192.0.2.1"),"locked")

    def test_forwarded_address_is_only_accepted_from_local_proxy(self):
        header={"X-Forwarded-For":"192.0.2.123, 198.51.100.5"}
        self.assertEqual(app.request_client_id("127.0.0.1",header),"198.51.100.5")
        self.assertEqual(app.request_client_id("203.0.113.2",header),"203.0.113.2")

    def test_request_budgets_expire_and_keep_clients_separate(self):
        with patch.object(app.time,"monotonic",return_value=100):
            self.assertTrue(all(app.allow_request("one","/api/traffic") for _ in range(12)))
            self.assertFalse(app.allow_request("one","/api/traffic"))
            self.assertTrue(app.allow_request("two","/api/traffic"))
            self.assertTrue(app.allow_request("one","/"))
        with patch.object(app.time,"monotonic",return_value=161):
            self.assertTrue(app.allow_request("one","/api/traffic"))

    def test_thread_limit_and_recovery_and_script_policy(self):
        server=app.DashboardHTTPServer(("127.0.0.1",0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        url=f"http://127.0.0.1:{server.server_port}"
        try:
            for _ in range(48):
                self.assertTrue(server.request_slots.acquire(blocking=False))
            with self.assertRaises(urllib.error.HTTPError) as blocked:
                urllib.request.urlopen(url)
            self.assertEqual(blocked.exception.code,503)
            blocked.exception.close()
            for _ in range(48):
                server.request_slots.release()
            with urllib.request.urlopen(url) as response:
                policy=response.headers["Content-Security-Policy"]
                self.assertIn("script-src 'self';",policy)
                self.assertNotIn("Python",response.headers["Server"])
                body=response.read().decode()
                self.assertNotIn("<script>",body)
                self.assertIn('/static/dashboard.js',body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
