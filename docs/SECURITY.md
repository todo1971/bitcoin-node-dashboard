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
- Der einmalige Installer bindet fest an `127.0.0.1` und benötigt ein zufälliges Zugangstoken.
- `/admin` benötigt ein starkes separates Passwort und schützt Änderungen zusätzlich durch CSRF- und Origin-Prüfungen.
- Nach fünf falschen Anmeldungen wird die Administration für 15 Minuten gesperrt.
- Root-Aktionen sind auf zwei vollständige, feste Update-Befehle und einen verzögerten Neustart des Dashboard-Dienstes begrenzt; Browserparameter werden nicht an Root übergeben.
- Die Admin-Logansicht darf per `sudo` nur die letzten 80 Zeilen der beiden festen Update-Units lesen; sie nimmt keine freien Journal-Parameter an und begrenzt die Antwort auf 32 KiB.
- Die root-eigenen Helfer akzeptieren keine Argumente, validieren Paketpfade und führen Updates außerhalb der Webdienst-Control-Group aus.
- Der Update-Cache `/var/cache/bitcoin-dashboard-updates` gehört root und hat Modus `0700`.
- Core-Uploads landen als einzige Ausnahme im festen StateDirectory-Pfad. Der Root-Updater kopiert sie vor der Prüfung in sein eigenes temporäres Verzeichnis.

Wird der Dashboard-Prozess vollständig kompromittiert, kann ein Angreifer die
festgelegten Update-Aufträge und einen Dashboard-Neustart anstoßen und die vom
Dienstbenutzer beschreibbare `.env` verändern, aber weder Root-Befehlsargumente
noch Paketpfade bestimmen. Dashboard-Pakete werden vor Installation getestet; Bitcoin-Core-
Pakete benötigen zusätzlich eine passende SHA256-Prüfsumme und eine gültige
Signatur aus dem root-kontrollierten Schlüsselbund. Diese Grenze hängt zwingend
davon ab, dass der root-eigene Update-Cache, Root-Helfer, Sudoers-Regel und Updater-Konfiguration
nicht durch den Benutzer `btc` beschreibbar sind.

Ein kompromittierter Dashboard-Prozess kann ein Core-Archiv im Uploadordner
ersetzen und den festen Updateauftrag starten. Das verschafft ihm dennoch keine
Auswahl einer Prüfsumme oder Signatur: Beide Dateien werden vom Root-Helfer über
eine fest vorgegebene HTTPS-Adresse bei `bitcoincore.org` geladen. Der Node wird
erst gestoppt, nachdem eine Signatur aus dem root-kontrollierten Schlüsselbund
und die SHA-256-Prüfsumme erfolgreich geprüft wurden.

## Öffentliche Informationen

Eine öffentliche Instanz zeigt bewusst einige ohnehin über das Bitcoin-P2P-Netz
beobachtbare Informationen, darunter Node-Version, Blockhöhe und öffentliche IP.
Peer-IP-Adressen werden derzeit nicht an den Browser ausgeliefert.

## Empfohlene Absicherung

- HTTPS über Let's Encrypt erzwingen.
- `/admin` niemals über unverschlüsseltes öffentliches HTTP verwenden.
- Optional Plesk-Passwortschutz oder IP-Freigabe aktivieren.
- Port 8787 und RPC-Port 8332 per Firewall blockiert lassen.
- `/var/lib/bitcoin-dashboard/.env` mit Modus `0600` für den Dienstbenutzer `btc` halten; über `/admin` nur erlaubte Betriebswerte bearbeiten.
- Bitcoin Core und das Betriebssystem regelmäßig aktualisieren.
- Reverse-Proxy-Rate-Limits ergänzen, falls die Instanz öffentlich stark genutzt wird.
- Port 8791 des einmaligen Installers niemals über Plesk, Firewall oder Reverse Proxy veröffentlichen.
- Webhook-Ziele ausschließlich per HTTPS konfigurieren und das Ziel als Geheimnis behandeln.

## Geheimnisse

Folgende Inhalte dürfen nicht in Git eingecheckt werden:

- RPC-Cookie-Inhalt
- RPC-Passwörter
- Wallet-Dateien, Seeds oder Private Keys
- TLS-Private-Keys
- persönliche Zugangstoken
- `DASHBOARD_GITHUB_TOKEN` aus `/var/lib/bitcoin-dashboard/.env`
- `ADMIN_TOKEN` aus `/var/lib/bitcoin-dashboard/.env`
- produktive SQLite-Datenbanken
- Webhook-URLs mit eingebetteten Zugangstoken

Die Datei `.env` wird deshalb durch `.gitignore` ausgeschlossen.

Das GitHub-Token erhält ausschließlich `Contents: Read-only` für das einzelne
Repository `bitcoin-node-dashboard`. Es wird in der nur für `btc` lesbaren Datei
`/var/lib/bitcoin-dashboard/.env` mit Modus `0600` gespeichert. Bei Ablauf oder
vermuteter Offenlegung wird es ersetzt und das alte Token bei GitHub widerrufen.

## Sicherheitsmeldungen

Da das Repository privat ist, sollten Sicherheitsprobleme zunächst als private
Nachricht an den Repository-Eigentümer gemeldet werden und nicht als öffentliches
Issue erscheinen.
