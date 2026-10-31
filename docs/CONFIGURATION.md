# Dashboard-Konfiguration

Deutsch | [English](en/CONFIGURATION.md)

Bei der systemd-Installation liest das Dashboard `/var/lib/bitcoin-dashboard/.env`. Unter `/home/btc/bitcoin-dashboard/.env` liegt ein symbolischer Link auf dieselbe Datei. Die echte Datei gehört dem Dienstbenutzer `btc` und hat Modus `0600`; das Programmverzeichnis bleibt für den laufenden Webdienst schreibgeschützt.

Unter `/admin` → **Dashboard-Konfiguration** können Node-Adresse, ZMQ-Endpunkt, Messintervalle, Aufbewahrung, Alarmgrenzen und -ziele sowie GitHub-Repository und -Token geändert werden. Der Editor prüft erlaubte Feldnamen und Werte, schreibt atomar und startet ausschließlich den fest vorgegebenen Dashboard-Dienst nach kurzer Verzögerung neu. Fehlschlägt schon die Planung des Neustarts, wird die vorherige Datei wiederhergestellt. Eine gültige Admin-Anmeldung, Same-Origin-Prüfung und CSRF-Token sind erforderlich.

Geheime Token werden nicht zurück an den Browser gegeben. Beim GitHub-Token bedeutet ein leeres Eingabefeld „unverändert“. `ADMIN_TOKEN`, Dienst-Bindung, RPC-Pfade, Datenbankpfad und Upload-Verzeichnis sind bewusst nicht über das Web änderbar. Diese Werte können bei Bedarf lokal als Root in der `.env` geändert werden; anschließend `sudo systemctl restart bitcoin-dashboard`.

## Bestehende Installation einmalig migrieren

1. Dashboard auf Version 1.13.0 aktualisieren. Die Migration benötigt zusätzlich den **neuen** `installer/bootstrap-admin.sh` aus dem Release-Archiv; der normale Dashboard-Updater installiert keine Root-Helfer.
2. Das Release-Archiv als Root in ein temporäres Verzeichnis entpacken und den Bootstrap ausführen:

   ```sh
   tmpdir=$(mktemp -d)
   tar -xzf bitcoin-node-dashboard-1.13.0.tar.gz -C "$tmpdir"
   sudo sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
   rm -rf -- "$tmpdir"
   ```

3. Der Bootstrap kopiert die bisherige `/etc/default/bitcoin-dashboard` **nur dann** in die neue `.env`, wenn dort noch keine Konfiguration existiert. Er richtet Service und eng begrenzte Neustartberechtigung neu ein. Die alte Datei bleibt zunächst als Rückfallkopie unverändert, wird aber vom Dienst nicht mehr gelesen.
4. Ohne Geheimnisse auszugeben prüfen:

   ```sh
   systemctl show bitcoin-dashboard -p EnvironmentFiles
   stat -c '%U:%G %a %n' /var/lib/bitcoin-dashboard/.env
   readlink /home/btc/bitcoin-dashboard/.env
   curl -fsS http://127.0.0.1:8787/healthz
   ```

5. `/admin` öffnen, eine harmlose Einstellung speichern und den Neustart prüfen. Erst nach erfolgreicher Kontrolle kann die alte `/etc/default/bitcoin-dashboard` als nicht mehr benötigte Kopie **gezielt** entfernt oder sicher archiviert werden.

Die Konfigurationsdatei und GitHub-Token niemals in ein Repository hochladen. `.env` ist in `.gitignore` ausgeschlossen. Bei Containerinstallationen bleibt die `.env` weiterhin durch Compose verwaltet; der Web-Editor ist dort deaktiviert.
