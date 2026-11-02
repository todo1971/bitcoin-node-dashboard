# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import unittest

from tools.check_documentation import has_encoding_damage


class DocumentationEncodingTests(unittest.TestCase):
    def test_valid_multilingual_text_is_preserved(self):
        self.assertFalse(has_encoding_damage('Prüfung, Größe, Änderungen · português, CONFIGURAÇÃO, 中文, русский'))

    def test_windows_misdecoding_and_replacement_characters_are_detected(self):
        for text in ('Prüfung', 'Größe', 'Änderung', 'Öffnen', 'Übersicht', 'Deutsch · English', 'A – B'):
            with self.subTest(text=text):
                broken = text.encode('utf-8').decode('cp1252')
                self.assertTrue(has_encoding_damage(broken))
        self.assertTrue(has_encoding_damage('Pr\ufffdfung'))
