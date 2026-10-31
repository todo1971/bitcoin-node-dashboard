"""List static UI text without an English catalog entry (technical labels included)."""
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads((ROOT / 'static/locales/en.json').read_text(encoding='utf-8'))


class Texts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = False

    def handle_data(self, data):
        data = data.strip()
        if data and not self.skip and data not in catalog:
            print(data)


if __name__ == '__main__':
    parser = Texts()
    for name in ('index.html', 'admin.html'):
        parser.feed((ROOT / 'static' / name).read_text(encoding='utf-8'))
