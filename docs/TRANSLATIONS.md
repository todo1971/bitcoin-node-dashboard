# Sprachen

Deutsch | [English](en/TRANSLATIONS.md)

Seit 1.18.0 gibt es Deutsch und Englisch. Die Auswahl steht unter dem Seitenkopf
des Dashboards und der Administration. Sie wird im Browser unter
`dashboard-language` gespeichert; ohne Auswahl bleibt Deutsch der Standard.
Ein Sprachwechsel lädt die Seite neu und erhält den aktiven Reiter.

Die UTF-8-Dateien `static/locales/de.json` und `static/locales/en.json`
verwenden dieselben deutschen Ausgangstexte als Schlüssel. Englische Werte
übersetzen ganze Texte oder bekannte Satzbestandteile dynamischer Meldungen.
Die längste passende Formulierung gewinnt; Wortgrenzen schützen Kennungen.
Es werden ausschließlich lokale Sprachdateien geladen.

Beschriftungen, bekannte Statusmeldungen, Hilfetexte und Glossar sind übersetzt.
Unbekannte serverseitige Meldungen bleiben Deutsch. Originalausgaben in
Protokollfeldern, Eingabewerte, Secrets und technische Kennungen werden nicht
übersetzt. Datums- und Zahlenformate richten sich nach Deutsch bzw. Englisch.
Kann der englische Katalog nicht geladen werden, erscheint ein Hinweis und
die deutsche Oberfläche bleibt bedienbar.

Bei neuen UI-Texten beide Kataloge ergänzen. `python tools/check_languages.py`
listet statische Texte ohne eigenen Katalogeintrag auf, darunter auch absichtlich
unveränderte technische Bezeichnungen. Neue Sprachen benötigen zusätzlich
einen Eintrag in Auswahl und URL-Allowlist in `app.py`.

Der normale Dashboard-Updater übernimmt das gesamte `static/`-Verzeichnis
einschließlich Sprachdateien. Es sind keine zusätzlichen Pakete erforderlich.

Prüfung: `python -m unittest discover -s tests -v`. Der optionale Browsertest
`node tools/test_languages.cjs` benötigt Playwright als Entwicklungswerkzeug;
mit `QA_BROWSER=msedge` kann eine vorhandene Edge-Installation genutzt werden.
Er prüft Sprachwechsel, Speicherung, Live-Texte, Wortgrenzen und unveränderte
Protokolle und Formularwerte.

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
