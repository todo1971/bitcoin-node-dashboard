# Sicherheitskonzept

## Grundsätze

- Der Webdienst bindet standardmäßig ausschließlich an `127.0.0.1`.
- Bitcoin-RPC-Port 8332 bleibt lokal und wird nicht über den Reverse Proxy geleitet.
- Der RPC-Cookie wird nicht an Browser oder externe Dienste übertragen.
- Der Browser kann keine frei gewählten RPC-Kommandos ausführen.
- Unterprozesse werden ohne Shell und mit festen Argumentstrukturen gestartet.
- Der Systemd-Service läuft ohne Root-Rechte als Benutzer `btc`.
- Nur `/var/lib/bitcoin-dashboard` ist als persistenter Schreibbereich vorgesehen.
- Browserantworten enthalten CSP-, Frame-, Referrer- und MIME-Sicherheitsheader.
- Installer und Wartungspanel binden fest an `127.0.0.1` und benötigen zufällige Zugangstoken.
- Root-Updates sind auf zwei feste, root-eigene Helfer ohne freie Argumente begrenzt.
- Das Admin-Service benötigt für diese beiden `sudo`-Helfer bewusst Privilegienwechsel; die Schreibbereiche seiner Systemd-Sandbox bleiben auf Programm-, Backup- und Lock-Verzeichnisse begrenzt.

## Öffentliche Informationen

Eine öffentliche Instanz zeigt bewusst einige ohnehin über das Bitcoin-P2P-Netz
beobachtbare Informationen, darunter Node-Version, Blockhöhe und öffentliche IP.
Peer-IP-Adressen werden derzeit nicht an den Browser ausgeliefert.

## Empfohlene Absicherung

- HTTPS über Let's Encrypt erzwingen.
- Optional Plesk-Passwortschutz oder IP-Freigabe aktivieren.
- Port 8787 und RPC-Port 8332 per Firewall blockiert lassen.
- `/etc/default/bitcoin-dashboard` nur für Root lesbar halten.
- Bitcoin Core und das Betriebssystem regelmäßig aktualisieren.
- Reverse-Proxy-Rate-Limits ergänzen, falls die Instanz öffentlich stark genutzt wird.
- Port 8790 und 8791 niemals über Plesk, Firewall oder Reverse Proxy veröffentlichen.
- Webhook-Ziele ausschließlich per HTTPS konfigurieren und das Ziel als Geheimnis behandeln.

## Geheimnisse

Folgende Inhalte dürfen nicht in Git eingecheckt werden:

- RPC-Cookie-Inhalt
- RPC-Passwörter
- Wallet-Dateien, Seeds oder Private Keys
- TLS-Private-Keys
- persönliche Zugangstoken
- produktive SQLite-Datenbanken
- Webhook-URLs mit eingebetteten Zugangstoken

Die Datei `.env` wird deshalb durch `.gitignore` ausgeschlossen.

## Sicherheitsmeldungen

Da das Repository privat ist, sollten Sicherheitsprobleme zunächst als private
Nachricht an den Repository-Eigentümer gemeldet werden und nicht als öffentliches
Issue erscheinen.
