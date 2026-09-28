# Changelog

Alle wesentlichen Änderungen dieses Projekts werden hier dokumentiert.

## 1.6.0 – 2026-09-28

- neuestes Dashboard-Release automatisch über die GitHub Releases API ermitteln
- private Repositorys über ein nur lesendes Fine-grained Token unterstützen
- Release-Archiv und separate SHA-256-Datei herunterladen und vor Installation prüfen
- installierte und neueste Dashboard-Version in `/admin` anzeigen
- weiterhin parameterloser, eng begrenzter Root-Updateauftrag mit Backup und Rollback

## 1.5.2 – 2026-09-28

- systemd-Optionen entfernt, die `NoNewPrivileges` indirekt aktivierten
- integrierte Update-Aufträge können dadurch die exakt erlaubten sudo-Regeln verwenden

## 1.5.1 – 2026-09-28

- Linux-Zeilenenden für alle Shell-Skripte im Release-Archiv erzwungen

## 1.5.0 – 2026-09-28

- Administration unter `/admin` in das Dashboard integriert
- separaten dauerhaft laufenden Admin-Webdienst entfernt
- starke Basic-Authentifizierung, CSRF-Prüfung und Anmeldesperre ergänzt
- Admin-POST-Anfragen auf Typ und Größe begrenzt und Cross-Origin-Anfragen blockiert
- nur zwei exakte, parameterlose Update-Aufträge über `sudo` zugelassen
- Updates in isolierte transiente systemd-Dienste ausgelagert
- alte Admin-Service-Installation wird beim Bootstrap entfernt

## 1.4.2 – 2026-09-28

- Speicherplatzalarm verständlich auf 90 Prozent Belegung umgestellt
- neue Variable `DISK_MAX_USED_PERCENT` ergänzt
- alte Variable `DISK_MIN_FREE_PERCENT` bleibt als Fallback kompatibel

## 1.4.1 – 2026-09-28

- Datenträgerkarte und Verlauf von freiem auf belegten Speicher umgestellt
- Alarmgrenze entsprach weiterhin weniger als 10 Prozent freiem Speicher

## 1.4.0 – 2026-09-28

- Alarme für RPC-Ausfall, Sync-Rückstand und fehlende Inbound-Peers ergänzt
- CPU-, RAM-, Datenträger- und bitcoind-Laufzeitmessung ergänzt
- Systemmetriken in SQLite-Historie und Diagrammen ergänzt
- optionale Benachrichtigung per lokalem Sendmail und HTTPS-Webhook ergänzt
- Versionsprüfung über den offiziellen Bitcoin-Core-Release-Index ergänzt
- Alarmkarenz, Wiederholsperre und Entwarnungen ergänzt

## 1.3.0 – 2026-09-28

- lokalen, token-geschützten Web-Installer ergänzt
- getrennte lokale Wartungsoberfläche ergänzt
- Dashboard-Updates mit Tests, Backup, Healthcheck und Rollback ergänzt
- Bitcoin-Core-Updates mit GPG- und SHA256-Prüfung ergänzt
- Beispielkonfiguration für neue Bitcoin-Nodes ergänzt
- Update-Berechtigungen auf zwei feste Root-Helfer begrenzt

## 1.2.1 – 2026-09-28

- Historienansichten für 1, 6 und 12 Stunden ergänzt
- Zeitachsen kurzer Ansichten auf Stunden und Minuten umgestellt

## 1.2.0 – 2026-09-28

- SQLite-Historie im WAL-Modus ergänzt
- Messintervall und Aufbewahrungsdauer konfigurierbar gemacht
- Diagramme für Peers und Gebührenschätzungen ergänzt
- feste Zeitbereiche von 24 Stunden bis zu einem Jahr ergänzt
- Systemd-StateDirectory für persistente Daten eingerichtet
- Datenbanktests ergänzt

## 1.1.0 – 2026-09-28

- externe Erreichbarkeitsprüfung über BTCNodes ergänzt
- direkte Suchlinks für BTCNodes und Bitnodes ergänzt
- öffentliche Adresse und Port konfigurierbar gemacht
- externe Abfrage auf fünf Minuten begrenzt
- Sicherheitsheader für Browserantworten ergänzt
- Dokumentation und CI-Struktur aufgebaut

## 1.0.0 – 2026-09-28

- erstes read-only Dashboard
- Node-, Netzwerk-, Mempool-, Gebühren- und Blockdaten
- Systemd-Service und Plesk-Reverse-Proxy-Beispiel
