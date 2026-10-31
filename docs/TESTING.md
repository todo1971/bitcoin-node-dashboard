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

## Tokenlose Updates

Anleitung und Grenzen: [Öffentliches Repository ohne Token](UPDATES.md#öffentliches-repository-ohne-token).
Ein Livetest mit dem öffentlichen offiziellen GitHub-CLI-Repository hat anonym
Metadaten und eine Prüfsummendatei mit dem vorhandenen Downloader geladen.
Solange dieses Dashboard-Repository privat ist, ist dessen eigener anonymer
End-to-End-Test nicht möglich.

## Prüfung vor der Veröffentlichung

Ein lesender Musterscan über 499 historische Git-Dateiobjekte fand vor diesen
Test-Ergänzungen keine Treffer für private Schlüssel, GitHub-/AWS-/Slack-/Telegram-
Tokens, Datenbank-Passwort-URLs, RPC-Auth-Hashes oder typische sensible Dateinamen.
Das ist eine begrenzte Prüfung und kein Beweis, dass alle denkbaren Geheimnisse
ausgeschlossen sind.

Die bekannte Server-IP steht weiterhin in Beispielen und Standardeinstellungen.
Git-Autoreninformationen gehören zur Historie. Eine Lizenz ist im README noch
nicht festgelegt. Die Sichtbarkeit des Repositorys wurde nicht geändert.
