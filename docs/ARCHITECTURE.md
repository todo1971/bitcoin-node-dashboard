# Architektur

Deutsch | [English](en/ARCHITECTURE.md)

```text
Browser
   │ HTTPS
   ▼
Plesk / Apache Reverse Proxy
   │ HTTP auf 127.0.0.1:8787
   ▼
Python-Dashboard (Benutzer btc)
   ├── bitcoin-cli ──► lokaler Bitcoin-Core-RPC
   ├── SQLite ────────► /var/lib/bitcoin-dashboard/history.sqlite3
   ├── HTTPS ────────► öffentliche BTCNodes-API / Bitcoin-Core-Version
   └── /admin ───────► exakt definierter transienter systemd-Updateauftrag
                              │
                              └── root-eigener, parameterloser Update-Helfer
```

## Lokale Daten

Das Dashboard führt nur eine fest definierte Liste lesender Aufrufe aus:

- `getblockchaininfo`
- `getnetworkinfo`
- `getmempoolinfo`
- `getnettotals`
- `getpeerinfo`
- `getblockstats`
- `estimatesmartfee`
- `getblockcount` für den Healthcheck
- `uptime`

Die Browseranwendung kann weder RPC-Methoden noch Argumente vorgeben. Antworten
werden zehn Sekunden zwischengespeichert, damit parallele Browseraufrufe den
Node nicht unnötig belasten.

## Administration

Die Administrationsoberfläche läuft im selben HTTP-Prozess, besitzt jedoch eine
separate starke Anmeldung, CSRF- und Origin-Prüfungen sowie eine Anmeldesperre.
Der Browser kann nur zwischen den Aktionen `dashboard` und `bitcoin` wählen.
Diese Auswahl wird intern auf zwei unveränderliche Befehlsfolgen abgebildet.

Die eigentliche privilegierte Arbeit läuft in einem transienten systemd-Dienst.
Sudoers erlaubt dem Dashboard-Benutzer ausschließlich diese beiden vollständigen
Aufrufe. Die root-eigenen Helfer akzeptieren keine Argumente und lesen Pakete nur
aus fest konfigurierten, für `btc` nicht beschreibbaren Verzeichnissen.

## Externe Daten

Für die öffentliche Sicht auf den Node wird ausschließlich die fest konfigurierte
Adresse bei `btcnodes.io` abgefragt. Das Ergebnis wird mindestens fünf Minuten
gespeichert. Ein Ausfall des externen Dienstes beeinflusst die lokalen Node-Daten
nicht.

## Historische Daten

Ein Hintergrund-Thread speichert standardmäßig jede Minute eine Messung in
SQLite. Die HTTP-Abfragen öffnen jeweils eine eigene kurzlebige Verbindung.
WAL-Modus und `busy_timeout` erlauben paralleles Lesen während der Messung. Das
übrige Dateisystem bleibt durch Systemd schreibgeschützt; nur das StateDirectory
ist beschreibbar.
