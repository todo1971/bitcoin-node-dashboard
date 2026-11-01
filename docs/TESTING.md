# Testumfang und öffentliche Updates

Deutsch | [English](en/TESTING.md)

## Lokale Umgebung am 31. Oktober 2026

Auf dem geprüften Windows-Rechner sind Docker Desktop, die Docker-CLI und eine
WSL-Linux-Distribution nicht installiert. Ein lokaler Containerstart wurde deshalb
nicht durchgeführt. Es wurde keine Containerumgebung installiert und kein Test
auf den produktiven Server verlagert.

## Containerprüfung in GitHub Actions

Die CI validiert alle drei Compose-Dateien und baut das Dashboard- sowie das
All-in-one-Image. Sie startet den All-in-one-Container mit Bitcoin Core und prüft
Healthcheck, englische Sprachdatei und die gesperrte Adminseite ohne Anmeldung.
Danach wird der getrennte Bitcoin-Core-/Dashboard-Stack gebaut und mit denselben
HTTP-Prüfungen gestartet. Beide Varianten nutzen temporäre Runner-Volumes.
Nur diese wegwerfbaren Test-Volumes werden am Ende entfernt.

Die Host-Node-Variante wird als Compose-Konfiguration validiert, aber nicht mit
einem echten Host-bitcoind gestartet. Ein bestandener CI-Test ersetzt keinen
lokalen Test unter Docker Desktop, keinen vollständigen Blockchain-Sync und
keinen Produktivbetrieb mit echten Wallets oder Langzeitdaten.

Compose-Images und Build-Metadaten verwenden denselben Versionsstandard;
`DASHBOARD_VERSION` kann ihn beim bewussten Bau einer anderen Version überschreiben.

## Peer- und Verkehrsprüfung ab 1.20.0

Die Python-Tests prüfen begrenzte Peer-Aggregate ohne Adressen oder freie
Clientkommentare, Zählerrückgänge und Laufzeit-Neustarts, Messlücken, UTC-Grenzen,
unbekannte Werte, die 20-Block-Grenze und die neuen lesenden HTTP-Endpunkte.
Die optionalen Playwright-Tests benötigen Playwright und einen Chromium-Browser
(`QA_BROWSER=msedge` für Edge). Sie prüfen alle sechs Sprachen, sichere Textausgabe,
Null gegenüber unbekannten Raten, Reiter und mobile Breiten. Die Browserdaten
sind Testdaten; dabei wird kein produktiver Node verändert.

```sh
python -m unittest discover -s tests -q
python tools/check_documentation.py
node tools/test_languages.cjs
node tools/test_node_insights.cjs
```

## Tokenlose Updates

Anleitung und Grenzen: [Öffentliches Repository ohne Token](UPDATES.md#öffentliches-repository-ohne-token).
Ein Livetest mit dem öffentlichen offiziellen GitHub-CLI-Repository hat anonym
Metadaten und eine Prüfsummendatei mit dem vorhandenen Downloader geladen.
Nach Veröffentlichung lässt sich derselbe lesende Test mit
`--repo todo1971/bitcoin-node-dashboard` direkt am Dashboard-Repository ausführen.

## Prüfung vor der Veröffentlichung

Ein lesender Musterscan über 499 historische Git-Dateiobjekte fand vor diesen
Test-Ergänzungen keine Treffer für private Schlüssel, GitHub-/AWS-/Slack-/Telegram-
Tokens, Datenbank-Passwort-URLs, RPC-Auth-Hashes oder typische sensible Dateinamen.
Das ist eine begrenzte Prüfung und kein Beweis, dass alle denkbaren Geheimnisse
ausgeschlossen sind.

Die bekannte Server-IP steht weiterhin in Beispielen und Standardeinstellungen.
Git-Autoreninformationen gehören zur Historie. Seit 1.18.4 ist die Lizenz
GPL-3.0-only festgelegt und das Repository für die öffentliche Nutzung vorgesehen.
