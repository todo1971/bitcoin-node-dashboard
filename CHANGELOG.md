# Changelog

Alle wesentlichen Änderungen dieses Projekts werden hier dokumentiert.

## 1.18.0 – 2026-10-31

- Deutsche und englische Sprachdateien unter `static/locales/` ergänzen.
- Sprachauswahl im Dashboard und Adminbereich anbieten; Auswahl lokal im Browser speichern.
- Statische Beschriftungen und bekannte dynamische Statusmeldungen übersetzen; Zahlen und Datum nach gewählter Sprache formatieren.
- Originalprotokolle, technische Diagnosen und Eingabewerte unverändert lassen. Unbekannte Meldungen fallen auf Deutsch zurück.
- Sprachdateien über eine feste öffentliche URL-Allowlist ausliefern; Admin-Authentifizierung bleibt erforderlich.

## 1.17.0 – 2026-10-10

- Startseite auf Node-Status, Synchronisation, Verbindungen und Alarme reduzieren
- Netzwerk, Analyse, Historie und System in getrennte, per Tastatur bedienbare Reiter aufteilen
- bestehende Messwerte und Datenquellen beibehalten; Diagramme beim Öffnen ihres Reiters in der sichtbaren Breite neu zeichnen
- Reiter und Zeitraum-Auswahl für schmale Displays anpassen

## 1.16.0 – 2026-10-10

- aktive Chain-Spitze und bis zu zwölf weitere Chain-Tips mit Status, Höhe, Zweiglänge und Block-Hash aus `getchaintips` anzeigen
- alle alternativen Tips nach Status zählen; RPC-Antwort 60 Sekunden zwischenspeichern
- per ZMQ beobachtete Block-Trennungen im gewählten Zeitraum separat zählen und letzten Zeitpunkt anzeigen
- Momentaufnahme und beobachtete Ereignisse ausdrücklich unterscheiden; fehlende Ereignisse bei Ausfällen nicht als Null-Reorg-Beweis darstellen

## 1.15.0 – 2026-10-10

- BTCNodes-Status als externen Verzeichniseintrag kennzeichnen; `found=false` bedeutet unbekannt statt „Node offline“ und löst keinen Port-Alarm aus
- Mempool-Gebührenverteilung nach sat/vB mit Transaktionszahl und virtuellen Bytes anzeigen
- Gebührenbereiche aus dem bereits vorhandenen, periodisch zwischengespeicherten `getrawmempool true`-Abruf berechnen; keine zusätzliche RPC-Abfrage und keine Speicherung einzelner Transaktions-IDs
- fehlende Gebührenangaben separat zählen und die Grenzen der Einzeltransaktions-Gebührenrate gegenüber CPFP-Paketpreisen erläutern

## 1.14.0 – 2026-10-01

- öffentliche Ereignis-Zeitleiste für Blöcke, Alarmwechsel, Node-/Dashboard-Neustarts, größere Peer-Abfälle und Dashboard-Versionswechsel
- ZMQ-Sequenzlücken, Verbindungsstörungen und nicht nachgetragene Blockstatistiken als Datenqualitäts-Hinweise historisieren
- nach ausgelassenen Blöcken höchstens zwölf aktuelle Blockstatistiken pro Durchlauf per lesendem RPC nachtragen; größere oder nicht verfügbare Lücken ausdrücklich kennzeichnen
- neue API `/api/timeline?range=24h`; Zeitbereich mit der Historie gekoppelt, Unterbrechungen in Diagrammen markiert
- fehlende Diagrammwerte nicht mehr als Null darstellen und Linien nicht über Messlücken hinweg verbinden

## 1.13.0 – 2026-09-30

- systemd-Konfiguration aus `/etc/default/bitcoin-dashboard` in die Dashboard-`.env` im State-Verzeichnis migrieren
- erlaubte Betriebswerte unter `/admin` bearbeiten, validieren, atomar speichern und den Dashboard-Dienst verzögert neu starten
- GitHub-Token im Editor nur als gesetzt/nicht gesetzt anzeigen; Admin-Token und interne Pfade bleiben geschützt
- alten Konfigurationsort nach der Migration als Rückfallkopie behalten

## 1.12.0 – 2026-09-30

- optionaler lokaler ZMQ-Subscriber für `zmqpubsequence`: Block- und Mempool-Ereignisse sowie Transportsequenzlücken zählen
- Ereigniszähler minutenweise in SQLite speichern, ohne Transaktions- oder Block-Hashes abzulegen
- Browser per Server-Sent Events aktualisieren; periodische Abfragen bleiben als Fallback
- Telegram-Benachrichtigungen für später in die Roadmap verschoben

## 1.11.9 – 2026-09-30

- Netzwerkansicht um Verbindungsdauer, Ping, Protokollversion, Transport v2 und beendete Peer-Verbindungen je IPv4/IPv6/Tor ergänzt
- kurzlebige Testverbindungen bei Peer-Wechseln ausgeschlossen; Node-Neustart setzt Zähler zurück
- Boot- und Dienstprüfung für bitcoind, Tor und Dashboard dokumentiert

## 1.11.8 – 2026-09-30

- Admin-Updateprotokoll zeigt den letzten Lauf als grünes „OK“, rotes „Nicht OK“ oder „Läuft …“ an
- Ausgabe wird auf den jeweils letzten gestarteten Update-Lauf eingegrenzt

## 1.11.7 – 2026-09-30

- Update-Journal für Dashboard und Bitcoin Core direkt auf `/admin` anzeigen und alle fünf Sekunden aktualisieren
- Journal-Zugriff auf zwei feste Units, 80 Zeilen und 32 KiB Antwort begrenzen
- einmaligen Bootstrap für die neue sudoers-Leseberechtigung dokumentieren

## 1.11.6 – 2026-09-30

- Updater-Paketablage in einen root-eigenen Cache unter `/var/cache` verlegt
- Installer migriert vorhandene Updater-Konfiguration beim erneuten Bootstrap
- alte Home-Verzeichnis-Pfade aus Anleitungen, Beispielen und Tests entfernt

## 1.11.5 – 2026-09-30

- vollständige Tor-Onion-Adresse als Knotenkennung im Bereich Node & Version anzeigen
- Kennung ausdrücklich von einer dauerhaften Bitcoin-Protokoll-ID unterscheiden

## 1.11.4 – 2026-09-30

- global gültige IPv6-Adressen der Server-Netzwerkschnittstellen zusätzlich anzeigen
- Server-IP ausdrücklich von einer durch Bitcoin Core gemeldeten P2P-Adresse unterscheiden

## 1.11.3 – 2026-09-30

- Peer-Richtungen im Dashboard als `in` und `out` beschriftet
- von Bitcoin Core gemeldete IPv4- und IPv6-Adressen neben der Onion-Adresse angezeigt; falls nicht gemeldet, die konfigurierte öffentliche P2P-IP gekennzeichnet

## 1.11.2 – 2026-09-30

- Startseite in Node & Version, Netzwerk, System sowie Statistiken & Analyse gegliedert
- Kennzahlen in die passenden Bereiche verschoben und Kartenbreiten angepasst

## 1.11.1 – 2026-09-30

- IPv4-, IPv6- und Tor-Verbindungen separat nach eingehenden und ausgehenden Peers anzeigen
- gemeldete Onion-Adresse des Nodes im Dashboard anzeigen

## 1.11.0 – 2026-09-29

- tägliche UTXO-Statistik über `gettxoutsetinfo none` ergänzt
- Blockgrößen und bestätigte Transaktionsraten historisiert
- periodische Mempool-Cluster-, RBF-Fähigkeits- und CPFP-Kandidatenanalyse ergänzt
- neue Analyseansicht mit Kennzahlen, Diagrammen, UTXO-Tabelle und Glossar
- neuer JSON-Endpunkt `/api/analytics`

## 1.10.0 – 2026-09-29

- sicherer Shell-Installer für die All-in-one-Variante ergänzt
- `--prepare-only` bereitet Installationen ohne Start oder Dienständerungen vor
- Plesk-Anleitung für Compose-Stacks und reine Apache-Systeme ergänzt
- getrennte Apache-Vorlage für das lokal gebundene Container-Dashboard
- Installer schützt vorhandene Dienste durch Prüfung belegter Ports

## 1.9.0 – 2026-09-29

- optionale All-in-one-Variante für Bitcoin Core und Dashboard ergänzt
- beide Prozesse laufen im gemeinsamen Container ohne Root-Rechte
- gemeinsames persistentes Volume mit getrennten Datenverzeichnissen
- RPC bleibt ausschließlich auf dem Loopback-Interface des Containers
- kombinierter Healthcheck und geordnetes Herunterfahren beider Prozesse

## 1.8.2 – 2026-09-29

- Healthcheck nach einem Dienstneustart wartet jetzt bis zu 30 Sekunden
- verhindert unnötige Rollbacks, während Python den HTTP-Port noch öffnet
- Zustand des wiederhergestellten Dienstes wird nach einem Rollback geprüft

## 1.8.1 – 2026-09-29

- Python-Tests des Root-Updaters verwenden jetzt ein separates, für den
  unprivilegierten Benutzer beschreibbares Bytecode-Verzeichnis
- Fehler `Permission denied: __pycache__` beim Dashboard-Update behoben

## 1.8.0 – 2026-09-29

- gehärtetes Dashboard-Image und Docker-Compose-Dateien ergänzt
- Varianten für vorhandenen Host-Node und vollständigen neuen Docker-Stack
- direkten JSON-RPC-Zugriff mit Cookie-Authentifizierung ergänzt
- Docker-Container ohne Docker-Socket, Host-systemd, Linux-Capabilities oder Root
- integrierte Root-Updates im Containerbetrieb deaktiviert und verständlich gekennzeichnet
- feste Bitcoin-Core-Version statt unkontrolliertem `latest` vorgesehen

## 1.7.0 – 2026-09-29

- Bitcoin-Core-Archiv per Dateiauswahl oder Drag-and-drop unter `/admin` hochladen
- Upload auf 200 MB, stabile Linux-Dateinamen und passende Serverarchitektur begrenzen
- Archiv ohne Root-Rechte in einem festen StateDirectory-Pfad zwischenspeichern
- `SHA256SUMS` und `SHA256SUMS.asc` ausschließlich von `bitcoincore.org` laden
- GPG-, SHA-256-, Plattform-, Versions- und Downgradeprüfung vor dem Stoppen des Nodes
- Upload nach erfolgreicher Installation entfernen; Backup und Rollback beibehalten
- Reverse-Proxy-Beispiele für große, langsamere Uploads ergänzen

## 1.6.2 – 2026-09-28

- temporäres Update-Verzeichnis für die Tests durch den Benutzer `btc` betretbar gemacht
- Schreibrechte bleiben weiterhin ausschließlich bei Root
- Regressionstest für die Reihenfolge von Verzeichnisfreigabe und Tests ergänzt

## 1.6.1 – 2026-09-28

- vollständige Einrichtung eines minimal berechtigten Fine-grained GitHub-Tokens dokumentiert
- sichere Speicherung, Funktionsprüfung, Ablauf und Widerruf des Tokens beschrieben
- geplanten, signaturgeprüften Bitcoin-Core-Upload im Adminbereich dokumentiert

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
