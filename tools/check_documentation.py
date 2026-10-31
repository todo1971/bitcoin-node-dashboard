# Copyright (C) 2026 Hardy (todo1971)
# SPDX-License-Identifier: GPL-3.0-only
"""Check bilingual coverage, local links, history and unchanged command examples."""
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]


def check():
    errors = []
    pairs = [(ROOT / name, ROOT / name.replace('.md', '.en.md')) for name in ('README.md', 'CHANGELOG.md')]
    pairs += [(file, ROOT / 'docs/en' / file.name) for file in sorted((ROOT / 'docs').glob('*.md'))]
    code = re.compile(r'^[ \t]*```[^\n]*\n([\s\S]*?)^[ \t]*```', re.M)
    for german, english in pairs:
        if not english.is_file():
            errors.append(f'Missing English counterpart: {english}')
            continue
        de, en = german.read_text(encoding='utf-8'), english.read_text(encoding='utf-8')
        for source, text, counterpart in ((german, de, english), (english, en, german)):
            links = re.findall(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)', text)
            resolved = []
            for link in links:
                url = urlparse(link)
                if url.scheme or not url.path:
                    continue
                target = (source.parent / unquote(url.path)).resolve()
                resolved.append(target)
                if not target.is_file():
                    errors.append(f'Broken link: {source.relative_to(ROOT)} -> {link}')
            if counterpart.resolve() not in resolved:
                errors.append(f'Missing language backlink: {source.relative_to(ROOT)}')
            if '{{CODE' in text:
                errors.append(f'Unexpanded code placeholder: {source}')
        if german.name == 'CHANGELOG.md':
            versions = r'^## (\d+\.\d+\.\d+) [–-] (\d{4}-\d{2}-\d{2})'
            if re.findall(versions, de, re.M) != re.findall(versions, en, re.M):
                errors.append('Changelog versions or dates do not match')
        elif german.name != 'ARCHITECTURE.md':
            de_blocks, en_blocks = code.findall(de), code.findall(en)
            # The README defaults block translates labels, not executable commands.
            if german.name == 'README.md':
                de_blocks, en_blocks = de_blocks[1:], en_blocks[1:]
            if de_blocks != en_blocks:
                errors.append(f'Command examples differ: {german.relative_to(ROOT)}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Documentation checked: {len(pairs)} bilingual pairs, local links, changelog versions/dates and command examples.')


if __name__ == '__main__':
    check()
