# Alarme und Systemüberwachung

Deutsch | [English](en/ALERTS.md)

## Überwachte Zustände

Das Dashboard prüft bei jeder Messung:

- Erreichbarkeit des lokalen Bitcoin-Core-RPC
- Abstand zwischen Blockhöhe und Headerhöhe sowie Initial Block Download
- Anzahl eingehender Peers
- freien Platz auf dem Datenträger des Bitcoin-Datadirs
- RAM-Auslastung des Hosts
- vom externen Crawler gemeldete Erreichbarkeit des öffentlichen P2P-Endpunkts, sofern verfügbar
- Verfügbarkeit einer neueren stabilen Bitcoin-Core-Version

CPU, RAM, freier Speicher und bitcoind-Laufzeit werden zusätzlich in SQLite
gespeichert. Das Dashboard zeigt die Datenträgerbelegung als belegten Anteil.
Der Speicherplatzalarm wird standardmäßig ab 90 Prozent Belegung ausgelöst.
Intern gespeicherte freie Werte bleiben für die historische Berechnung erhalten.
Ein fehlender Verzeichniseintrag bedeutet unbekannt, nicht offline. Die externe
Auskunft ist kein eigener Live-Porttest.

## Alarmverhalten

Ein Fehler muss zunächst die konfigurierte Karenzzeit überschreiten. Erst dann
wird er als aktiver Alarm angezeigt und versendet. Solange er besteht, erfolgt
höchstens nach Ablauf der Wiederholsperre eine weitere Nachricht. Bei Rückkehr
zum Normalzustand wird eine Entwarnung versendet und der Alarm geschlossen.

Ein Versionshinweis erscheint ebenfalls als Alarm, löst aber niemals selbst
ein Update aus. Bitcoin-Core-Updates bleiben eine bewusste Administratoraktion.

## Benachrichtigungen einrichten

In der Dashboard-`.env` (`/var/lib/bitcoin-dashboard/.env`) oder unter
`/admin` → Dashboard-Konfiguration können beide Kanäle unabhängig aktiviert werden:

```text
ALERT_EMAIL=admin@example.com
ALERT_WEBHOOK_URL=https://monitoring.example.com/hooks/GEHEIMES-TOKEN
```

Für E-Mail muss auf dem Server ein funktionierendes `sendmail`-kompatibles
Programm vorhanden sein, zum Beispiel aus der bestehenden Postfix-Installation.
Der Webhook erhält einen JSON-POST mit `subject`, `message`, `host` und
`timestamp`. Es werden ausschließlich HTTPS-Ziele akzeptiert.

Nach Änderungen ist der Dienst neu zu starten:

```bash
sudo systemctl restart bitcoin-dashboard
sudo journalctl -u bitcoin-dashboard -n 50 --no-pager
```

Die aktiven Zustände sind außerdem ohne Versandkanal im roten Alarmfeld des
Dashboards und unter `/api/alerts` sichtbar.
