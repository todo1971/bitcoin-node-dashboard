# Copyright (C) 2026 Hardy (todo1971)
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only live check of anonymous release discovery and a small asset download."""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='cli/cli', help='Public GitHub repository; defaults to the official GitHub CLI')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo):
        parser.error('Expected OWNER/REPOSITORY')
    script = Path(__file__).resolve().parents[1] / 'installer/fetch-dashboard-release'
    loader = importlib.machinery.SourceFileLoader('fetcher', str(script))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    fetcher = importlib.util.module_from_spec(spec)
    loader.exec_module(fetcher)
    metadata = json.loads(fetcher.request_bytes(f'https://api.github.com/repos/{args.repo}/releases/latest', '', 'application/vnd.github+json', 1_000_000))
    candidates = [asset for asset in metadata.get('assets', []) if ('checksum' in asset['name'].lower() or asset['name'].endswith('.sha256')) and 0 < asset['size'] <= 4096]
    if not candidates:
        raise SystemExit('No small checksum asset available for this smoke test')
    asset = candidates[0]
    content = fetcher.request_bytes(asset['url'], '', 'application/octet-stream', 4096)
    if not re.search(rb'\b[0-9a-fA-F]{64}\b', content) or content.lstrip().startswith(b'{'):
        raise SystemExit('Asset did not return checksum content')
    digest = asset.get('digest')
    if digest and digest != 'sha256:' + hashlib.sha256(content).hexdigest():
        raise SystemExit('Asset digest mismatch')
    print(f"Anonymous public release check passed: {args.repo} {metadata['tag_name']}, {asset['name']}, {len(content)} bytes. No token supplied; no installation performed.")


if __name__ == '__main__':
    main()
