#!/usr/bin/env python3
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
"""Check Docker Hub indexes before builds; never print the anonymous pull token."""
import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPT = 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'


def inspect_image(repository, tag):
    query = urllib.parse.urlencode({'service':'registry.docker.io', 'scope':f'repository:{repository}:pull'})
    with urllib.request.urlopen('https://auth.docker.io/token?' + query, timeout=30) as response:
        token = json.load(response)['token']
    request = urllib.request.Request(
        f'https://registry-1.docker.io/v2/{repository}/manifests/{tag}',
        headers={'Authorization':'Bearer ' + token, 'Accept':ACCEPT})
    with urllib.request.urlopen(request, timeout=30) as response:
        index = json.load(response)
        digest = response.headers.get('Docker-Content-Digest')
    platforms = []
    for manifest in index.get('manifests', []):
        platform = manifest.get('platform', {})
        if platform.get('os') == 'linux':
            platforms.append({**platform, 'digest':manifest['digest']})
    architectures = {platform['architecture'] for platform in platforms}
    if not {'amd64', 'arm64'} <= architectures:
        raise RuntimeError(f'{repository}:{tag} lacks required architectures: {architectures}')
    return {'image':f'{repository}:{tag}', 'digest':digest, 'platforms':platforms}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional JSON evidence file; contains no credentials')
    args = parser.parse_args()
    dockerfile = (ROOT / 'Dockerfile.all-in-one').read_text(encoding='utf-8')
    core = re.search(r'^ARG BITCOIN_CORE_VERSION=([0-9.]+)$', dockerfile, re.M).group(1)
    python_tag = re.search(r'^FROM python:([^\s]+)$', dockerfile, re.M).group(1)
    dashboard_python = re.search(r'^FROM python:([^\s]+)$', (ROOT / 'Dockerfile').read_text(encoding='utf-8'), re.M).group(1)
    references = [('bitcoin/bitcoin', core), ('library/python', python_tag)]
    if dashboard_python != python_tag:
        references.append(('library/python', dashboard_python))
    results = [inspect_image(repository, tag) for repository, tag in references]
    for result in results:
        print(f'{result["image"]}: linux/amd64 + linux/arm64 available ({result["digest"]})')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
