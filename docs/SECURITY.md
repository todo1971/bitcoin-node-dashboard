# Sicherheit und einmalige Umstellung ab 1.24

Deutsch | [English](en/SECURITY.md)

Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>

## Vertrauensgrenzen

Die Host-Installation trennt das Dienstkonto `bitcoin-dashboard` vom Bitcoin-Core-Konto. Dashboard-Code liegt unter `/opt/bitcoin-dashboard` und gehört root. Beschreibbar bleiben ausschließlich die Zustandsdaten unter `/var/lib/bitcoin-dashboard`. Die `.env` und `rpc.auth` gehören dem Dashboard-Konto mit Modus 0600. Das Dashboard liest bei lokalen Nodes einen eigenen RPC-Zugang, nicht den vollständigen Node-Cookie.

Der lokale RPC-Zugang erlaubt ausschließlich: `getblockchaininfo`, `getnetworkinfo`, `getmempoolinfo`, `getnettotals`, `getpeerinfo`, `uptime`, `getblockstats`, `getblock`, `getrawmempool`, `getchaintips`, `gettxoutsetinfo`, `getblockcount`, `estimatesmartfee`. Andere bereits vorhandene RPC-Benutzer behalten ihre Rechte. Bei einem extern betriebenen Node muss dessen Administrator diese Beschränkung dort selbst einrichten. Container werden durch diesen Host-Bootstrap nicht migriert; dort Updates extern verwalten und RPC-Zugänge separat beschränken.

Die Updatequelle und ein optionales GitHub-Token stehen für Root-Updates ausschließlich in `/etc/bitcoin-dashboard-updater.conf` (root:root, 0600). Die Weboberfläche kann sie nicht ändern. Angaben in der Dashboard-`.env` dienen gegebenenfalls nur der unprivilegierten Versionsanzeige. Das öffentliche Projekt benötigt keinen Token. HTTPS und ein vertrauenswürdiger GitHub-Account bleiben Teil der Vertrauenskette: Eine SHA-256-Datei aus demselben Release ersetzt keine unabhängige Signatur.

## Einmalige Migration

Ein normales Dashboard-Update ersetzt keine Root-Helfer. Deshalb muss der Bootstrap aus dem bewusst ausgewählten und geprüften Release **einmal als root** ausgeführt werden. Nicht aus einem vom Dashboard-Konto beschreibbaren Checkout starten. Die folgenden Befehle in einer Root-Shell ausführen:

```bash
install -d -m 0700 /root/bitcoin-dashboard-release
cd /root/bitcoin-dashboard-release
curl -fL -O https://github.com/todo1971/bitcoin-node-dashboard/releases/download/v1.25.0/bitcoin-node-dashboard-1.25.0.tar.gz
curl -fL -O https://github.com/todo1971/bitcoin-node-dashboard/releases/download/v1.25.0/bitcoin-node-dashboard-1.25.0.tar.gz.sha256
sha256sum -c bitcoin-node-dashboard-1.25.0.tar.gz.sha256
tmpdir=$(mktemp -d /root/bitcoin-dashboard-release/unpack.XXXXXX)
tar -xzf bitcoin-node-dashboard-1.25.0.tar.gz -C "$tmpdir"
sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
systemctl enable bitcoin-dashboard
curl -fsS http://127.0.0.1:8787/healthz
```

Vorher ein eigenes Backup anlegen. Der Bootstrap sichert außerdem Zustand, ursprüngliche Dienste und Helfer unter `/var/backups/bitcoin-dashboard/hardening-*`. Die Sicherung enthält Geheimnisse und bleibt nur für root zugänglich. Die erste lokale Migration startet **Dashboard und Bitcoin Core neu**, ohne den Server neu zu starten. Bestehende Historie und ein ausreichend langes Admin-Passwort bleiben erhalten. Ein neues Passwort wird bei Bedarf in der geschützten `.env` erzeugt und nicht ausgegeben; lokal mit `sudoedit /var/lib/bitcoin-dashboard/.env` verwalten.

Für einen lokalen systemd-Node wird ein expliziter `-conf=...`-Pfad und ein eigenes Core-Dienstkonto vorausgesetzt. Der Bootstrap übernimmt den bisherigen Konfigurationsinhalt, ergänzt die RPC-Freigaben und schreibt ihn nach `/etc/bitcoin-dashboard/bitcoin.conf` (root und Core-Gruppe, 0640). Ein Drop-in für `bitcoind.service` verwendet diese Konfiguration und die nach `/usr/local/lib/bitcoin-core/bin` kopierten, root-eigenen Programme. Der vorhandene `-datadir` bleibt erhalten. Künftige Core-Konfigurationsänderungen müssen an der neuen aktiven Datei erfolgen. Die ursprüngliche Datei wird nicht gelöscht. Sonderkonfigurationen mit Includes, weiteren Drop-ins oder externen Nodes vorher prüfen.

Bei einem Fehler stellt der Bootstrap die gesicherten Dienstdateien, Programmdateien, Zustandsdaten und deren Eigentümer wieder her und versucht den vorher laufenden Dienst erneut zu starten. Backups und Journal anschließend prüfen; auch ein Rollback kann durch externe Fehler scheitern. Ein wiederholter Bootstrap behält die Zugangsdaten bei. Bei unveränderter RPC-Freigabe wird Core nicht erneut gestartet; ab 1.25 wird bei Bedarf `getblock` ergänzt und Core dafür neu gestartet.

## Schutz der Weboberfläche

Admin-Zugriff erfordert Basic-Authentifizierung, mindestens 32 Zeichen Passwort, CSRF- und Origin-Prüfung. Fünf falsche Anmeldungen sperren nur die betroffene Client-Adresse vorübergehend. Ausschließlich bei einem Loopback-Proxy wird der letzte Eintrag von `X-Forwarded-For` als Client verwendet. Der Reverse Proxy muss die tatsächliche Client-Adresse anhängen oder den Header ersetzen; den Dashboard-Port nicht öffentlich freigeben.

Pro Client gelten 240 Anfragen pro Minute und zusätzlich zwölf teure Historien-/Analyseabfragen pro Minute. Es gibt höchstens 48 gleichzeitige HTTP-Handler, 15 Sekunden Socket-Lesezeit und 16 SSE-Verbindungen. Überschreitungen erhalten 429 oder 503. Externe Skripte und Inline-JavaScript sind durch die Content Security Policy gesperrt. Der HTTP-Server meldet keine Python- oder Dashboard-Versionsnummer.

Root-Helfer prüfen Eigentümer und Schreibrechte sämtlicher Pfadkomponenten. Archive werden vor dem ersten Entpacken vollständig auf Pfade, Größe, Duplikate und Dateitypen geprüft. Links und Spezialdateien werden abgelehnt. Anwendungstests und Core-Versionsabfragen laufen unprivilegiert. Dashboard-Updates ersetzen einen geschützten Programmbaum und rollen bei fehlgeschlagener Funktionsprüfung zurück; Root importiert dabei keinen Dashboard-Code. Core-Uploads werden ohne Symlink-Folgen in einen geschützten Bereich kopiert und benötigen weiterhin gültige GPG-Signaturen und SHA-256.

## Prüfung und Grenzen

Regressionstests prüfen Archivangriffe, fremde Updatequellen, Redirects, getrennte Anmeldesperren und begrenzte HTTP-Handler. Die CI verwendet zusätzlich echten Bitcoin Core im Regtest in einer Wegwerfumgebung auf AMD64 und ARM64: getrennte Konten, erlaubte und abgelehnte RPC-Abfragen, geschützte Pfade und Wiederherstellung nach absichtlich fehlgeschlagenem Neustart. Dies ersetzt weder einen Penetrationstest noch eine Sicherung der Produktivinstallation.

GitHub schützt `main` durch erfolgreiche CI-Prüfungen; Secret Scanning, Push Protection und Dependabot sind aktiviert. Neue Funktionen werden eigenständig entwickelt. Hinweise auf Sicherheitsprobleme ohne Zugangsdaten an hb@308-arms.de melden.
