import hashlib
import importlib.machinery
import importlib.util
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
    def test_downloads_only_versioned_assets_after_checksum_match(self):
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
            update_root = root / "home" / "todo"
            target = root / "target"
            target.mkdir()
            (target / "app.py").write_text('__version__ = "1.0.0"\n')
            env_file.write_text(
                "DASHBOARD_GITHUB_REPOSITORY=example/project\n"
                "DASHBOARD_GITHUB_TOKEN=test-token\n"
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
                            ):
                                result = release_fetcher.main()

            self.assertEqual(result, 0)
            self.assertEqual(
                (update_root / "bitcoin-node-dashboard-update.tar.gz").read_bytes(),
                archive,
            )

if __name__ == "__main__":
    unittest.main()
