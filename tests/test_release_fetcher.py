import hashlib
import importlib.machinery
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parent.parent / "installer" / "fetch-dashboard-release"
LOADER = importlib.machinery.SourceFileLoader("release_fetcher", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
release_fetcher = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(release_fetcher)


class ReleaseFetcherTests(unittest.TestCase):
    def test_anonymous_asset_request_has_no_authorization_header(self):
        with patch.object(release_fetcher.urllib.request, 'urlopen', return_value=io.BytesIO(b'archive')) as request:
            self.assertEqual(release_fetcher.request_bytes('https://api.github.com/repos/example/public/releases/assets/1', '', 'application/octet-stream', 100), b'archive')
        headers = request.call_args.args[0].headers
        self.assertNotIn('Authorization', headers)
        self.assertEqual(headers['Accept'], 'application/octet-stream')

    def test_private_asset_request_preserves_authorization(self):
        with patch.object(release_fetcher.urllib.request, 'urlopen', return_value=io.BytesIO(b'archive')) as request:
            release_fetcher.request_bytes('https://api.github.com/repos/example/private/releases/assets/1', 'test-token', 'application/octet-stream', 100)
        self.assertEqual(request.call_args.args[0].get_header('Authorization'), 'Bearer test-token')

    def test_update_root_is_fixed_to_root_controlled_cache(self):
        self.assertTrue(
            release_fetcher.safe_update_root(
                Path("/var/cache/bitcoin-dashboard-updates")
            )
        )
        self.assertFalse(release_fetcher.safe_update_root(Path("/home/other/updates")))

    def test_downloads_only_versioned_assets_after_checksum_match(self):
        for token in ('test-token', ''):
            with self.subTest(authenticated=bool(token)):
                self.check_versioned_download(token)

    def check_versioned_download(self, token):
        archive = b"safe release archive"
        digest = hashlib.sha256(archive).hexdigest()
        metadata = json.dumps(
            {
                "tag_name": "v2.0.0",
                "assets": [
                    {
                        "name": "bitcoin-node-dashboard-2.0.0.tar.gz",
                        "url": "https://api.github.com/assets/1",
                    },
                    {
                        "name": "bitcoin-node-dashboard-2.0.0.tar.gz.sha256",
                        "url": "https://api.github.com/assets/2",
                    },
                ],
            }
        ).encode()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / "dashboard.env"
            config_file = root / "updater.conf"
            update_root = root / "cache" / "bitcoin-dashboard-updates"
            target = root / "target"
            target.mkdir()
            (target / "app.py").write_text('__version__ = "1.0.0"\n')
            env_file.write_text(
                "DASHBOARD_GITHUB_REPOSITORY=example/project\n"
                f"DASHBOARD_GITHUB_TOKEN={token}\n"
            )
            config_file.write_text(
                f"UPDATE_ROOT={update_root}\nDASHBOARD_TARGET={target}\n"
            )

            responses = [metadata, f"{digest}  archive\n".encode(), archive]
            with patch.object(release_fetcher, "ENV_FILE", env_file):
                with patch.object(release_fetcher, "UPDATER_CONFIG", config_file):
                    with patch.object(release_fetcher.os, "geteuid", return_value=0, create=True):
                        with patch.object(release_fetcher, "safe_update_root", return_value=True):
                            with patch.object(
                                release_fetcher,
                                "request_bytes",
                                side_effect=responses,
                            ) as request_bytes:
                                result = release_fetcher.main()
                                self.assertEqual([call.args[1] for call in request_bytes.call_args_list], [token, token, token])

            self.assertEqual(result, 0)
            self.assertEqual(
                (update_root / "bitcoin-node-dashboard-update.tar.gz").read_bytes(),
                archive,
            )

if __name__ == "__main__":
    unittest.main()
