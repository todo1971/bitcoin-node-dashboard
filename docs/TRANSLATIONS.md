# Sprachen

Deutsch | [English](en/TRANSLATIONS.md)

Seit 1.19.0 stehen sechs Oberflächensprachen zur Verfügung; Deutsch und Englisch
gab es bereits seit 1.18.0. Die Auswahl steht unter dem Seitenkopf
des Dashboards und der Administration. Sie wird im Browser unter
`dashboard-language` gespeichert; ohne Auswahl bleibt Deutsch der Standard.
Ein Sprachwechsel lädt die Seite neu und erhält den aktiven Reiter.

| Sprache | Katalog | Zahlen-/Datumsformat |
|---|---|---|
| Deutsch | `de.json` | `de-DE` |
| English | `en.json` | `en-GB` |
| Español | `es.json` | `es-ES` |
| Português (Brasil) | `pt-BR.json` | `pt-BR` |
| 简体中文 | `zh-Hans.json` | `zh-CN` |
| Русский | `ru.json` | `ru-RU` |

Die UTF-8-Dateien unter `static/locales/` enthalten jeweils denselben vollständigen
Satz von 300 deutschen Ausgangstexten als Schlüssel. Die übersetzten Werte
übersetzen ganze Texte oder bekannte Satzbestandteile dynamischer Meldungen.
Die längste passende Formulierung gewinnt; Wortgrenzen schützen Kennungen.
Es werden ausschließlich lokale Sprachdateien geladen.

Beschriftungen, bekannte Statusmeldungen, Hilfetexte und Glossar sind übersetzt.
Unbekannte serverseitige Meldungen bleiben Deutsch. Originalausgaben in
Protokollfeldern, Eingabewerte, Secrets und technische Kennungen werden nicht
übersetzt. Datums- und Zahlenformate richten sich nach Deutsch bzw. Englisch.
Kann der gewählte Katalog nicht geladen werden, erscheint ein Hinweis in dessen Sprache und
die deutsche Oberfläche bleibt bedienbar.

Bei neuen UI-Texten alle sechs Kataloge ergänzen. `python tools/check_languages.py`
listet statische Texte ohne eigenen Katalogeintrag auf, darunter auch absichtlich
unveränderte technische Bezeichnungen. Neue Sprachen benötigen zusätzlich
einen Eintrag in Auswahl und URL-Allowlist in `app.py`.

Der normale Dashboard-Updater übernimmt das gesamte `static/`-Verzeichnis
einschließlich Sprachdateien. Es sind keine zusätzlichen Pakete erforderlich.

Prüfung: `python -m unittest discover -s tests -v`. Der optionale Browsertest
`node tools/test_languages.cjs` benötigt Playwright als Entwicklungswerkzeug;
mit `QA_BROWSER=msedge` kann eine vorhandene Edge-Installation genutzt werden.
Er prüft alle sechs Sprachen: Sprachwechsel, Speicherung und erhaltenen Reiter,
Live-Texte, vollständige Update-Bestätigungen, Wortgrenzen, Desktop-/Mobilansicht
sowie unveränderte Protokolle und Formularwerte. Ungültige gespeicherte Sprachen
und fehlende Kataloge werden ebenfalls geprüft. `QA_SCREENSHOT_DIR` aktiviert
optional Screenshots. Chinesische und kyrillische Darstellung wurden zusätzlich
visuell kontrolliert. Der Observer markiert seine eigenen Textänderungen, damit
Übersetzungen nicht erneut übersetzt werden.

Die Projektdokumentation bleibt auf Deutsch und Englisch. Die vier zusätzlichen
Sprachen betreffen die Oberfläche, Admin-Hinweise und das Glossar. Japanisch und
traditionelles Chinesisch sind nicht enthalten. Fachsprachliche Verbesserungen
können als Pull Request in den jeweiligen Katalog eingebracht werden.

## Dokumentationssprachen

Seit 1.18.1 ergänzen [README.en.md](../README.en.md),
[CHANGELOG.en.md](../CHANGELOG.en.md) und `docs/en/` die deutschen Fassungen.
Jede Seite verlinkt ihr Gegenstück. Beide Changelogs enthalten sämtliche
historischen Versionen. Änderungen an Anleitungen in beiden Sprachen pflegen;
Befehle, Konfigurationsnamen, Pfade und historische Versionsdaten abgleichen.

Der normale Updater übernimmt alle englischen Seiten unter `docs/en/`.
Damit auch die beiden englischen Dateien im Projektwurzelverzeichnis lokal
mitinstalliert werden, muss der Root-Helfer einmal über den Bootstrap aus dem
geprüften 1.18.1-Release aktualisiert werden. Auf GitHub sind beide Dateien
unabhängig davon direkt verfügbar.
