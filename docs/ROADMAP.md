# Roadmap

## Umgesetzt in 1.2

- Messwerte regelmäßig in SQLite speichern
- Diagramme für 1, 6, 12 und 24 Stunden sowie 7 Tage, 30 Tage und 1 Jahr

## Nächste Ausbaustufe

- Alarme bei Node-Ausfall, Sync-Rückstand oder fehlenden Inbound-Peers
- Überwachung von Festplattenspeicher, CPU, RAM und Prozesslaufzeit
- Versionsprüfung für Bitcoin Core

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
