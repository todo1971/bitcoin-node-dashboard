# Roadmap

Deutsch | [English](en/ROADMAP.md)

## Umgesetzt in 1.20

- Peer-Softwareversionen, Service-Flags und Verbindungsarten aggregieren
- Verkehrsraten und gemessene Zeitraum-/Tages-/Monatssummen mit Messabdeckung
- Letzte 20 lokal erfasste Blöcke

## Umgesetzt in 1.2

- Messwerte regelmäßig in SQLite speichern
- Diagramme für 1, 6, 12 und 24 Stunden sowie 7 Tage, 30 Tage und 1 Jahr

## Umgesetzt in 1.3

- lokaler Web-Installer
- separates Wartungspanel über SSH-Tunnel
- Dashboard- und Bitcoin-Core-Updatehelfer
- Backups, Healthchecks und automatischer Rollback bei Startfehlern

## Umgesetzt in 1.5

- Administration in `/admin` integriert
- separaten Admin-Webdienst entfernt
- Authentifizierung, CSRF-Schutz, Rate-Limit und feste transiente Update-Aufträge ergänzt

## Umgesetzt in 1.6

- neueste Dashboard-Version über GitHub Releases ermitteln
- Release-Archiv automatisch laden und per SHA-256 prüfen
- private Repositorys mit minimal berechtigtem Fine-grained Token unterstützen

## Umgesetzt in 1.7

- Upload des offiziellen Bitcoin-Core-Archivs per Dateiauswahl oder Drag-and-drop
- Prüfsummen und Signaturen automatisch von `bitcoincore.org` laden
- Plattform, Version, Signaturen und Downgrade-Schutz vor dem Root-Update prüfen

## Umgesetzt in 1.8

- gehärtetes Dashboard-Containerimage
- Compose-Variante für den vorhandenen Host-Node
- optionaler vollständiger Stack mit Bitcoin Core und privatem RPC-Netz
- direkter JSON-RPC-Zugriff ohne `bitcoin-cli` im Dashboard-Container

## Umgesetzt in 1.9

- optionaler gemeinsamer Container für Bitcoin Core und Dashboard
- kombinierter Healthcheck für RPC und Weboberfläche
- kontrolliertes Beenden beider Prozesse mit ausreichender Shutdown-Frist

## Umgesetzt in 1.10

- vorbereitender und ausführender Shell-Installer für All-in-one
- Plesk-Installation wahlweise als Stack oder hinter Apache ohne nginx
- Schutz vor belegten Ports und unsicheren symbolischen Links

## Umgesetzt in 1.4

- Alarme bei Node-Ausfall, Sync-Rückstand oder fehlenden Inbound-Peers
- Überwachung von Festplattenspeicher, CPU, RAM und Prozesslaufzeit
- Versionsprüfung für Bitcoin Core

## Nächste Ausbaustufe

- Umgesetzt in 1.13: Dashboard-`.env` über `/admin` für ausgewählte Betriebswerte bearbeiten
- Umgesetzt in 1.14: Ereignis-Zeitleiste, bekannte Erfassungslücken und begrenzter Block-RPC-Nachtrag
- Umgesetzt in 1.15: BTCNodes-Status korrekt als Verzeichnisauskunft einordnen und lokale Mempool-Gebührenverteilung anzeigen

- Prometheus-Endpunkt für externe Langzeitüberwachung
- optional getrennte Schwellenwerte je Alarm im Wartungspanel bearbeiten
- zusätzliche Benachrichtigungskanäle wie Telegram oder ntfy

## Netzwerkdiagnose

- beendete Peer-Verbindungen über Dashboard-Neustarts hinweg historisieren
- Peer-Adressen in öffentlichen Ansichten maskieren
- Umgesetzt in 1.16: Chain-Tips per `getchaintips` und beobachtete Block-Trennungen per ZMQ getrennt darstellen
- externe Erreichbarkeit über mehrere unabhängige Beobachter vergleichen

## Echtzeit

- Umgesetzt in 1.12: neue Blöcke und Mempool-Ereignisse über lokales `zmqpubsequence` empfangen
- Umgesetzt in 1.12: Browseraktualisierung per Server-Sent Events mit Abfrage-Fallback
- Später: Telegram-Benachrichtigungen (E-Mail und Webhook existieren bereits)

## Erweiterte Analyse

- tägliche UTXO-Statistik
- Blockgrößen, Gebühren und Transaktionsraten historisieren
- Mempool-Cluster und RBF/CPFP-Pakete analysieren
- Prometheus-Endpunkt und optionale Grafana-Dashboards

## Separate Großprojekte

- eigener Mempool-/Blockexplorer
- Electrum-Server beziehungsweise Electrs-Indexer
- watch-only Adressüberwachung
- P2P-Anomalieerkennung mit Bitcoin-Core-Tracepoints

Ein vollständiger Explorer benötigt wesentlich mehr Speicher und Indizes als das
aktuelle Dashboard. Auf einem Pruned Node sind historische Abfragen nur begrenzt
möglich.
