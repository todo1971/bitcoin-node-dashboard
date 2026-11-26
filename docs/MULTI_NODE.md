# Mehrere Bitcoin-Nodes

Deutsch | [English](en/MULTI_NODE.md)

Ab Version 1.27 kann eine öffentliche Dashboard-Oberfläche mehrere unabhängige
Nodes anzeigen. Die Auswahl über den Reitern lädt die Seite mit `?node=ID` neu.
Der aktive Reiter und die Sprache bleiben beim Wechsel erhalten.

## Datenerfassung

Auf jedem Node-Server läuft eine eigene Dashboard-Instanz als Collector.
Sie fragt den lokalen Bitcoin Core ab und speichert ihre Messwerte in ihrer
eigenen SQLite-Datenbank. Auch CPU, RAM und Festplattenwerte stammen damit vom
ausgewählten Server. Vorhandene Historien werden nicht zusammengeführt.
Für einen neuen Collector beginnt die Historie mit seiner Einrichtung.
Ein nicht erreichbarer Collector zeigt einen Fehler und unbekannte Werte.

Der öffentliche Hauptserver leitet ausschließlich die öffentlichen Leseabfragen
und SSE-Ereignisse weiter. Administration und Updates gelten für den Hauptnode.
In einer entfernten Node-Ansicht ist der Administrationslink ausgeblendet.
Entfernte Collectors werden über SSH durch den Betreiber aktualisiert.

## Verbindung

Collector und Bitcoin-RPC lauschen nur auf Loopback. Ein dauerhafter SSH-Tunnel
verbindet einen lokalen Port des Hauptservers mit dem Collector-Port des
entfernten Servers. Der RPC-Port wird nicht veröffentlicht oder weitergeleitet.
Der Collector benötigt ein eigenes RPC-Konto mit den in [Sicherheit](SECURITY.md)
aufgeführten Lesemethoden. Seine Umgebung enthält `ADMIN_UPDATES_ENABLED=0`,
einen leeren `ADMIN_TOKEN`, `BITCOIN_RPC_URL=http://127.0.0.1:8332` und
`BITCOIN_COOKIE` mit dem Pfad zu seiner geschützten RPC-Zugangsdaten-Datei.
`BITCOIN_DATADIR`, `DISK_MONITOR_PATH` und `PUBLIC_NODE_ADDRESS` beziehen sich
auf den entfernten Node. Eine optionale ZMQ-Verbindung bleibt ebenfalls lokal.

Die mitgelieferte [Collector-Dienstdatei](../installer/bitcoin-dashboard-collector.service)
verwendet den Dienstbenutzer `bitcoin-dashboard`, root-eigenen Programmcode unter
`/opt/bitcoin-dashboard` und schreibbare Zustandsdaten unter
`/var/lib/bitcoin-dashboard`. Das Konto benötigt keine sudo-Rechte und keinen
Zugriff auf die vollständige Core-Cookie-Datei. Python 3.11 oder neuer,
CA-Zertifikate, systemd und OpenSSH werden benötigt. PyZMQ ist optional.

Für den Tunnel ein eigenes Schlüsselpaar und ein dediziertes SSH-Konto verwenden.
Den öffentlichen Schlüssel mit `restrict,port-forwarding,permitopen="127.0.0.1:8787"`
beschränken. In einem `Match User`-Abschnitt des SSH-Servers
`AllowTcpForwarding local`, `PermitTTY no` und `AllowAgentForwarding no` setzen.
Den Hostschlüssel vorab prüfen und mit `StrictHostKeyChecking=yes` fest pinnen.
Der private Tunnelschlüssel bleibt beim Hauptserver und ist für den
Dashboard-Prozess unlesbar. Das SSH-Passwort gehört in keine Dashboard-Konfiguration.

Beispiel für den Tunnelprozess mit systemd-Neustart bei Fehlern und automatischem Start
nach einem Serverneustart. Die Schlüsseldateien gehören dem separaten Tunnelkonto.

```sh
ssh -NT -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o UserKnownHostsFile=/var/lib/bitcoin-node-tunnel/known_hosts \
  -i /var/lib/bitcoin-node-tunnel/id_ed25519 \
  -L 127.0.0.1:18787:127.0.0.1:8787 bitcoin-node-tunnel@NODE_HOST
```

## Hauptserver konfigurieren

Die Datei `/etc/bitcoin-dashboard/nodes.json` gehört root und ist für den
Dashboard-Benutzer lesbar. `DASHBOARD_NODES_FILE` kann einen anderen Pfad vorgeben.
Diese Infrastrukturdatei wird vom Administrator verwaltet und vom Webeditor nicht
verändert. Updater ersetzen sie nicht.

```json
{
  "local_name": "Primary node",
  "nodes": [
    {
      "id": "second",
      "name": "Second node",
      "url": "http://127.0.0.1:18787"
    }
  ]
}
```

Die IDs sind eindeutig und enthalten nur Kleinbuchstaben, Ziffern und Bindestriche,
beginnend mit einem Buchstaben. `local` ist reserviert. Es sind maximal 16 weitere
Nodes möglich. Die URLs müssen HTTP-Loopback-Adressen mit explizitem Port sein.
Öffentliche URLs, Zugangsdaten im URL und Weiterleitungen werden abgewiesen.
Ohne Konfigurationsdatei bleibt die bisherige Einzelnode-Ansicht erhalten.
Änderungen an dieser Datei werden bei der nächsten Abfrage wirksam.

`/api/nodes` liefert nur IDs und Anzeigenamen. `/api/nodes/ID/history` und die
anderen freigegebenen öffentlichen Lese-Endpunkte liefern Daten des Collectors.
Interne URLs und RPC-Zugangsdaten werden nicht ausgegeben. Die Weiterleitung
ignoriert Client-Cookies und Authorization-Header, begrenzt JSON-Antworten auf
4 MiB und erlaubt maximal acht gleichzeitige entfernte SSE-Verbindungen.
Zeitlimits und Anfrageratenbegrenzungen gelten auch für entfernte Abfragen.
Die aggregierten Messwerte aller eingerichteten Nodes sind auf dem öffentlichen
Dashboard sichtbar. Einzelne Peer-Adressen werden dadurch nicht veröffentlicht.

## Prüfen

```sh
curl --fail http://127.0.0.1:18787/healthz
curl --fail http://127.0.0.1:8787/api/nodes
curl --fail http://127.0.0.1:8787/api/nodes/second/dashboard
curl --fail 'http://127.0.0.1:8787/api/nodes/second/history?range=1h'
```

Auf beiden Servern prüfen, ob die jeweilige Datenbank neue Messpunkte erhält.
Die erste Sammlung kann einige Sekunden benötigen. Beim Initial Block Download
sind Gebühren- und Mempoolanalysen je nach Core-Zustand noch unvollständig.
Die entfernte Administration, POST-Abfragen und unbekannte IDs müssen fehlschlagen.

Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
