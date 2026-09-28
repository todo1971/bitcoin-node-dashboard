# Sichere Updates

## Trennung vom öffentlichen Dashboard

Die Wartungsoberfläche läuft separat auf `127.0.0.1:8790`. Sie wird niemals über
Plesk oder einen öffentlichen Reverse Proxy veröffentlicht. Zugriff erfolgt nur
über einen SSH-Tunnel und HTTP-Basic-Authentifizierung mit einem zufälligen
Passwort.

Installation der Wartungsoberfläche:

```bash
sudo sh /home/btc/bitcoin-dashboard/installer/bootstrap-admin.sh
```

Das Script zeigt das Passwort einmal an. Anschließend lokal:

```bash
ssh -L 8790:127.0.0.1:8790 trading-server
```

Dann `http://127.0.0.1:8790` öffnen.

## Dashboard aktualisieren

Das gewünschte Release-Paket wird unter dem festen Namen bereitgestellt:

```bash
sudo cp /home/todo/bitcoin-node-dashboard-1.4.1.tar.gz \
  /home/todo/bitcoin-node-dashboard-update.tar.gz
```

Danach kann **Dashboard aktualisieren** gewählt werden. Der Helfer:

1. sperrt parallele Updates,
2. verwirft Archive mit unsicheren Pfaden oder Symlinks,
3. führt Kompilierung und Unit-Tests als Dashboard-Benutzer aus,
4. legt ein Backup unter `/var/backups/bitcoin-dashboard` an,
5. installiert nur die erlaubten Anwendungsdateien,
6. startet den Dienst neu,
7. prüft `/healthz` und führt bei einem Fehler einen Rollback aus.

Die Systemd-Unit und Sudoers-Dateien werden durch diesen Updater bewusst nicht
aus einem Update-Archiv überschrieben.

## Bitcoin Core aktualisieren

Bitcoin-Core-Updates sind immer manuell vorbereitet. Beispiel für Version
`VERSION` und die passende Plattform:

```text
/home/todo/bitcoin-core-update/
├── version
├── bitcoin-VERSION-x86_64-linux-gnu.tar.gz
├── SHA256SUMS
└── SHA256SUMS.asc
```

In `version` steht ausschließlich die Versionsnummer, beispielsweise `32.0`.
Alle drei Release-Dateien müssen aus demselben offiziellen Release-Verzeichnis
unter `https://bitcoincore.org/bin/bitcoin-core-VERSION/` stammen.

### Vertrauenswürdige Signaturschlüssel

Der Updater benötigt:

```text
/usr/local/share/bitcoin-core/trustedkeys.gpg
```

Schlüssel können aus dem offiziellen Repository `bitcoin-core/guix.sigs` bezogen
werden. Sie dürfen jedoch erst importiert werden, nachdem der jeweilige
Fingerprint über eine unabhängige, vertrauenswürdige Quelle geprüft wurde:

```bash
sudo install -d -o root -g root -m 0755 /usr/local/share/bitcoin-core
sudo gpg --batch --no-default-keyring \
  --keyring /usr/local/share/bitcoin-core/trustedkeys.gpg \
  --import /PFAD/ZUM/VERIFIZIERTEN-SCHLUESSEL.gpg
sudo chmod 0644 /usr/local/share/bitcoin-core/trustedkeys.gpg
```

Der Updater verlangt mindestens eine gültige Signatur aus diesem Keyring und
eine exakt passende SHA256-Prüfsumme. Erst danach stoppt er den Node, sichert die
vorhandenen Binärdateien, installiert das Release und startet den Dienst. Bei
einem Startfehler werden die bisherigen Binärdateien wiederhergestellt.

Major-Releases sollten vorab anhand der Release Notes und auf Änderungen an
Konfiguration, Wallet und Datenbankformat geprüft werden. Unbeaufsichtigte
automatische Bitcoin-Core-Updates sind absichtlich nicht vorgesehen.

## Root-Konfiguration

Pfade und Service-Namen stehen in:

```text
/etc/bitcoin-dashboard-updater.conf
```

Die Datei muss `root:root` gehören und darf nicht durch `deploybot` beschreibbar
sein. Die Sudoers-Regel erlaubt ausschließlich:

```text
/usr/local/sbin/update-bitcoin-dashboard
/usr/local/sbin/update-bitcoin-core
```
