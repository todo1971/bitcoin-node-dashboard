# Dashboard-Konfiguration

Deutsch | [English](en/CONFIGURATION.md)

Die systemd-Installation liest `/var/lib/bitcoin-dashboard/.env`. Unter `/opt/bitcoin-dashboard/.env` liegt ein Link darauf. Die Datei gehört dem eigenen Konto `bitcoin-dashboard` mit Modus 0600; Programmcode gehört root.

Unter `/admin` lassen sich Node-Adresse, ZMQ, Messintervalle, Aufbewahrung und Alarmwerte ändern. Erlaubte Feldnamen und Werte werden geprüft, die Datei atomar ersetzt und ausschließlich der feste Dashboard-Dienst neu gestartet. Bei fehlgeschlagener Neustartplanung wird die vorherige Datei wiederhergestellt. Admin-Anmeldung, Same-Origin und CSRF-Prüfung sind erforderlich.

`ADMIN_TOKEN`, Dienstbindung, RPC- und Datenbankpfade sind nur lokal durch root editierbar. Die Root-Updatequelle und ein optionales GitHub-Token stehen separat in `/etc/bitcoin-dashboard-updater.conf`; sie können nicht im Browser geändert werden. Der öffentliche Download benötigt keinen Token. Änderungen der Dashboard-`.env` benötigen einen Dashboard-Neustart.

Die [einmalige Sicherheitsmigration ab 1.24](SECURITY.md) übernimmt vorhandene Werte. `/etc/default/bitcoin-dashboard` wird nur verwendet, wenn noch keine State-`.env` existiert. Bestehende Geheimnisse bleiben geschützt und werden nicht ausgegeben.

```bash
systemctl show bitcoin-dashboard -p EnvironmentFiles
stat -c '%U:%G %a %n' /var/lib/bitcoin-dashboard/.env
readlink /opt/bitcoin-dashboard/.env
curl -fsS http://127.0.0.1:8787/healthz
```

Konfiguration niemals in Git aufnehmen. Container verwalten ihre Umgebung über Compose; dort ist der Webeditor deaktiviert.
