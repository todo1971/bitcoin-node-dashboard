# Roadmap

## Umgesetzt in 1.2

- Messwerte regelmäßig in SQLite speichern
- Diagramme für 1, 6, 12 und 24 Stunden sowie 7 Tage, 30 Tage und 1 Jahr

## Umgesetzt in 1.3

- lokaler Web-Installer
- separates Wartungspanel über SSH-Tunnel
- Dashboard- und Bitcoin-Core-Updatehelfer
- Backups, Healthchecks und automatischer Rollback bei Startfehlern

## Umgesetzt in 1.4

- Alarme bei Node-Ausfall, Sync-Rückstand oder fehlenden Inbound-Peers
- Überwachung von Festplattenspeicher, CPU, RAM und Prozesslaufzeit
- Versionsprüfung für Bitcoin Core

## Nächste Ausbaustufe

- Prometheus-Endpunkt für externe Langzeitüberwachung
- optional getrennte Schwellenwerte je Alarm im Wartungspanel bearbeiten
- zusätzliche Benachrichtigungskanäle wie Telegram oder ntfy

## Netzwerkdiagnose

- Peer-Versionen, Netze, Service-Flags und Pingzeiten aggregieren
- Verbindungsdauer und wiederkehrende Abbrüche darstellen
- Peer-Adressen in öffentlichen Ansichten maskieren
- Chain-Tips und Reorganisationen mit `getchaintips` überwachen
- externe Erreichbarkeit über mehrere unabhängige Beobachter vergleichen

## Echtzeit

- neue Blöcke über lokales ZMQ empfangen
- Mempool-Ereignisse über `zmqpubsequence` verarbeiten
- Browseraktualisierung per Server-Sent Events oder WebSocket
- Benachrichtigungen per E-Mail oder Telegram

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
