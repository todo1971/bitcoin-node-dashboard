# Roadmap

## Nächste Ausbaustufe

- Messwerte regelmäßig in SQLite speichern
- Diagramme für 24 Stunden, 7 Tage und 30 Tage
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
