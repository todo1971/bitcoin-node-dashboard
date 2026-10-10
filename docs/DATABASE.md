# Datenbank und Datenmenge

## Warum SQLite?

Das Dashboard besitzt genau einen schreibenden Prozess und erzeugt bei einem
Messintervall von 60 Sekunden rund 1.440 Datensätze täglich beziehungsweise
525.600 Datensätze jährlich. Diese Last liegt deutlich innerhalb des sinnvollen
SQLite-Bereichs. Ein zusätzlicher MariaDB-Dienst würde für diese Datenmenge mehr
Administration, Benutzerverwaltung, Netzwerkfläche und Backups erfordern, ohne
einen messbaren Vorteil zu liefern.

Die Datenbank läuft im WAL-Modus. Dadurch blockieren Diagrammabfragen die
laufende Messung nicht. Die Aufbewahrungsdauer ist standardmäßig auf 365 Tage
begrenzt.

## Schema

Die Tabelle `node_samples` enthält pro Messzeitpunkt:

- Blockhöhe und Synchronisationsfortschritt
- belegten Blockchain-Speicher
- Peer-Zahlen nach Richtung
- Mempool-Anzahl, Größe und Speicherbedarf
- Mempool-Mindestgebühr
- Gebührenschätzungen für 2, 6 und 12 Blöcke
- kumulierten Netzwerkverkehr
- Transaktionen und Gesamtgebühren des neuesten Blocks
- Blockgröße und bestätigte Transaktionsrate des neuesten Blocks
- CPU- und RAM-Auslastung
- freier Datenträgerplatz im Bitcoin-Datadir
- Laufzeit des bitcoind-Prozesses

Die Tabelle `alert_states` hält Beginn, Aktivierungszustand und letzte
Benachrichtigung eines Alarms fest. Dadurch bleiben Karenzzeit und
Wiederholsperre auch nach einem Dashboard-Neustart wirksam.

`dashboard_events` speichert die öffentliche Ereignis-Zeitleiste (Zeitpunkt,
Typ und kurze, adressfreie Meldung). `dashboard_meta` merkt sich die letzte
Dashboard-Version, damit ein Versionswechsel erkennbar ist.
`block_observations` speichert Blockstatistiken nach Blockhöhe. Wenn zwischen
zwei Messungen Blöcke fehlen, werden höchstens zwölf aktuelle Höhen pro
Durchlauf mit `getblockstats` nachgetragen. Bei größeren Lücken oder nicht
verfügbaren RPC-Daten bleibt ein sichtbarer Datenqualitäts-Hinweis; historische
Mempool-ZMQ-Ereignisse lassen sich dadurch nicht rekonstruieren.
Eine Reorganisation wird in der Zeitleiste markiert; bereits gespeicherte
Blockstatistiken derselben Höhe sind jedoch keine revisionssichere Chain-Historie.

Die Tabelle `utxo_samples` speichert höchstens einmal täglich die mit
`gettxoutsetinfo none` ermittelte Anzahl der UTXOs, Blockhöhe, Datenbankgröße
und Gesamtmenge. Der Modus `none` vermeidet die teure Berechnung eines
UTXO-Set-Hashes. Das Intervall lässt sich mit `UTXO_SAMPLE_SECONDS` ändern.

Die Mempool-Analyse wird nicht dauerhaft gespeichert. Sie fasst die
aktuellen Eltern-/Kind-Beziehungen als Cluster zusammen, kennzeichnet
RBF-fähige Transaktionen und CPFP-Kandidaten mit höherer Kind-Gebührenrate.
Aus demselben `getrawmempool true`-Abruf entsteht die Gebührenverteilung: die
Einzeltransaktions-Gebührenrate `fees.base / vsize` wird in feste sat/vB-Bereiche
eingeordnet; gezeigt werden Anzahl und Summe virtueller Bytes pro Bereich.
Fehlende oder ungültige Angaben werden gesondert gezählt. Die Einordnung ist
eine lokale Momentaufnahme und bildet effektive CPFP-Paketpreise nicht ab.
Sie wird standardmäßig höchstens alle fünf Minuten erneuert
(`MEMPOOL_ANALYSIS_SECONDS`); Transaktions-IDs werden nicht gespeichert.

Die API liefert keine halbe Million Rohdatensätze an den Browser. Sie verdichtet
die Daten abhängig vom ausgewählten Zeitraum in feste Zeitfenster:

| Ansicht | Zeitfenster | maximal ungefähr |
|---|---:|---:|
| 1 Stunde | 1 Minute | 60 Punkte |
| 6 Stunden | 2 Minuten | 180 Punkte |
| 12 Stunden | 5 Minuten | 144 Punkte |
| 24 Stunden | 5 Minuten | 288 Punkte |
| 7 Tage | 30 Minuten | 336 Punkte |
| 30 Tage | 2 Stunden | 360 Punkte |
| 1 Jahr | 1 Tag | 365 Punkte |

## Sicherung

Für eine konsistente Online-Sicherung sollte die SQLite-Backup-Funktion verwendet
werden:

```bash
sudo -u btc sqlite3 /var/lib/bitcoin-dashboard/history.sqlite3 \
  ".backup '/var/lib/bitcoin-dashboard/history-backup.sqlite3'"
```

## Wann MariaDB sinnvoll wird

Ein Wechsel ist sinnvoll, wenn mehrere Nodes gleichzeitig schreiben, Messungen
mehrmals pro Sekunde erfolgen, mehrere Dashboard-Prozesse parallel laufen oder
externe Analysewerkzeuge dauerhaft komplexe Abfragen ausführen. Die aktuelle
API trennt Datenerfassung und Ausgabe bereits so, dass später ein alternatives
Speicher-Backend ergänzt werden kann.
