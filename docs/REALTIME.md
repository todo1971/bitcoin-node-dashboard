# Echtzeit über Bitcoin Core ZMQ

Das Dashboard kann Block- und Mempool-Ereignisse aus `zmqpubsequence` empfangen. Der ZMQ-Endpunkt ist **nur lokal** erreichbar; der Browser verbindet sich ausschließlich mit dem Dashboard (`/api/events`, Server-Sent Events). Ohne ZMQ bleibt die bisherige periodische Abfrage aktiv.

## Aktivierung auf dem Host

1. Python-Bindings installieren: `sudo apt install python3-zmq`. Das Paket muss für den Python-Interpreter des Dashboard-Dienstes verfügbar sein.
2. In `/home/btc/bitcoin-data/bitcoin.conf` ergänzen: `zmqpubsequence=tcp://127.0.0.1:28332`.
3. In der Environment-Datei des Dashboard-Dienstes ergänzen: `ZMQ_SEQUENCE_ENDPOINT=tcp://127.0.0.1:28332`.
4. Bitcoin Core bei Gelegenheit geplant neu starten; danach das Dashboard neu starten. Vorher Dienstnamen mit `systemctl list-units '*bitcoin*'` prüfen. **Nicht** pauschal `bitcoind.service` voraussetzen. Beim Core-Neustart sind kurze Unterbrechungen zu erwarten.
5. Prüfen:

   ```sh
   sudo -u btc /home/btc/bin/bitcoin-cli -datadir=/home/btc/bitcoin-data -rpccookiefile=/home/btc/bitcoin-core/.bitcoin/.cookie getzmqnotifications
   ss -lntp | grep 28332
   curl -N http://127.0.0.1:8787/api/events
   curl -s http://127.0.0.1:8787/api/realtime
   ```

`getzmqnotifications` sollte `pubsequence` mit `tcp://127.0.0.1:28332` melden. Beim SSE-Test folgen auf `: connected` regelmäßig Heartbeats. Hinter Plesk/Apache auch den öffentlichen HTTPS-Pfad `/api/events` mit `curl -N` prüfen; eine vorgeschaltete Proxy-Schicht kann Streaming puffern oder Verbindungen begrenzen.

## Bedeutung und Grenzen

- `block_connected` und `block_disconnected` zählen verbundene beziehungsweise getrennte Blöcke (Reorg möglich).
- `mempool_added` und `mempool_removed` zählen Ereignisse, nicht den aktuellen Mempool-Bestand. Entfernung wegen Blockaufnahme ist kein `R`-Ereignis.
- Die Dashboard-Kacheln zeigen die aktuelle Minute, gespeichert in SQLite. Es werden keine Transaktions- oder Block-Hashes aus dem ZMQ-Stream gespeichert.
- Die 4-Byte-Transportsequenz erkennt Lücken **während einer laufenden Subscriber-Verbindung**. Neustarts, Verbindungsabbrüche und die anfängliche Subscribe-Phase können Ereignisse verlieren, ohne dass eine Lücke sicher nachweisbar ist. Nach einer Lücke lädt der Browser den aktuellen RPC-Stand erneut; vergangene Ereigniszähler werden nicht rückwirkend rekonstruiert.
- Bei gestörter SSE-Verbindung schaltet die Oberfläche auf periodische Abfragen zurück. Maximal zwölf gleichzeitige SSE-Verbindungen sind zugelassen.
- Ein ZMQ-Publisher authentifiziert seine Abonnenten nicht. Deshalb **niemals** an `0.0.0.0` oder eine öffentliche Adresse binden.

Telegram ist als spätere Erweiterung in der Roadmap notiert.
