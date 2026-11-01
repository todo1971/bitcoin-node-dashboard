# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import app


class LanguageAssetsTests(unittest.TestCase):
    languages = ('de', 'en', 'es', 'pt-BR', 'zh-Hans', 'ru')

    def test_catalog_keys_match_and_german_is_identity(self):
        catalogs = {lang: json.loads((app.STATIC_DIR / 'locales' / f'{lang}.json').read_text(encoding='utf-8')) for lang in self.languages}
        self.assertEqual(set(path.stem for path in (app.STATIC_DIR / 'locales').glob('*.json')), set(self.languages))
        for language, catalog in catalogs.items():
            with self.subTest(language=language):
                self.assertEqual(set(catalogs['de']), set(catalog))
                self.assertTrue(all(isinstance(v, str) and v for v in catalog.values()))
        self.assertTrue(all(k == v for k, v in catalogs['de'].items()))

    def test_assets_are_public_without_exposing_other_files(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            for path in ('/static/i18n.js', '/static/node-insights.js', *(f'/static/locales/{lang}.json' for lang in self.languages)):
                with urllib.request.urlopen(base + path) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(response.read())
            for path in ('/static/../app.py', '/static/locales/../../.env', '/static/locales/fr.json', '/static/locales/ja.json', '/static/locales/zh-Hant.json'):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
                error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
