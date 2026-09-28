# Architektur

```text
Browser
   │ HTTPS
   ▼
Plesk / Apache Reverse Proxy
   │ HTTP auf 127.0.0.1:8787
   ▼
Python-Dashboard (Benutzer btc)
   ├── bitcoin-cli ──► lokaler Bitcoin-Core-RPC
   └── HTTPS ────────► öffentliche BTCNodes-API
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

Die Browseranwendung kann weder RPC-Methoden noch Argumente vorgeben. Antworten
werden zehn Sekunden zwischengespeichert, damit parallele Browseraufrufe den
Node nicht unnötig belasten.

## Externe Daten

Für die öffentliche Sicht auf den Node wird ausschließlich die fest konfigurierte
Adresse bei `btcnodes.io` abgefragt. Das Ergebnis wird mindestens fünf Minuten
gespeichert. Ein Ausfall des externen Dienstes beeinflusst die lokalen Node-Daten
nicht.

## Zustandslosigkeit

Version 1.1 speichert keine Messwerte und benötigt keine Datenbank. Historische
Diagramme sind für eine spätere Version vorgesehen. Dadurch kann der Dienst mit
einem weitgehend schreibgeschützten Dateisystem laufen.
