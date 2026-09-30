# Sichere Updates

## Integrierte Administration

Die Wartungsoberfläche ist unter `/admin` in das Dashboard integriert. Sie
verwendet ein zufälliges Passwort mit mindestens 32 Zeichen, HTTP-Basic-
Authentifizierung, einen zusätzlichen CSRF-Token, eine globale Sperre nach fünf
Fehlversuchen sowie Größen-, Methoden- und Origin-Prüfungen.

Die Root-Helfer und das Passwort werden aus dem temporär entpackten, zuvor
geprüften Release-Paket eingerichtet. Das Archiv liegt dafür im aktuellen Verzeichnis:

```bash
tmpdir=$(mktemp -d)
sudo tar -xzf ./bitcoin-node-dashboard-1.11.8.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/bootstrap-admin.sh"
sudo rm -rf -- "$tmpdir"
```

Das Script zeigt Benutzername und Passwort an. Danach ist die Seite unter der
HTTPS-Adresse des Dashboards plus `/admin` erreichbar. Alternativ kann sie über
einen SSH-Tunnel auf den normalen Dashboard-Port geöffnet werden. Ein zweiter
Webprozess oder Port wird nicht mehr verwendet.

## Dashboard aktualisieren

Das Dashboard fragt die GitHub Releases API ab. Weil das Repository privat ist,
wird ein Fine-grained Personal Access Token mit ausschließlich lesendem
`Contents`-Zugriff auf dieses eine Repository benötigt. Es wird nur auf dem
Server gespeichert:

```bash
sudo editor /etc/default/bitcoin-dashboard
```

```text
DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard
DASHBOARD_GITHUB_TOKEN=github_pat_...
```

Danach den Dienst neu starten:

```bash
sudo chmod 0640 /etc/default/bitcoin-dashboard
sudo chown root:root /etc/default/bitcoin-dashboard
sudo systemctl restart bitcoin-dashboard
```

Unter `/admin` werden installierte und neueste Release-Version angezeigt. Bei
**Dashboard aktualisieren** übergibt die Webanwendung keine Browserparameter an
Root. Sie darf nur einen exakt festgelegten transienten systemd-Auftrag starten.
Der Root-Helfer:

1. sperrt parallele Updates,
2. ermittelt das neueste GitHub-Release,
3. lädt Archiv und separate SHA-256-Datei herunter und verifiziert beide,
4. verwirft Archive mit unsicheren Pfaden oder Symlinks,
5. führt Kompilierung und Unit-Tests als Dashboard-Benutzer aus,
6. legt ein Backup unter `/var/backups/bitcoin-dashboard` an,
7. installiert nur die erlaubten Anwendungsdateien,
8. startet den Dienst neu,
9. prüft `/healthz` und führt bei einem Fehler einen Rollback aus.

Jedes GitHub-Release benötigt zwei Assets mit genau diesen Namen:

```text
bitcoin-node-dashboard-VERSION.tar.gz
bitcoin-node-dashboard-VERSION.tar.gz.sha256
```

Die Systemd-Unit, Root-Helfer und Sudoers-Dateien werden durch diesen Updater
bewusst nicht aus einem Update-Archiv überschrieben. Nach dem Upgrade auf 1.11.6
einmalig `installer/bootstrap-admin.sh` aus dem entpackten Release als root
ausführen: Es aktualisiert die Helfer und verlegt die Paketablage in den
root-eigenen Cache `/var/cache/bitcoin-dashboard-updates`. Erst danach wird
die bisherige Ablage nicht mehr benötigt.

Ab 1.11.7 zeigt `/admin` die letzten 80 Journalzeilen der beiden Update-Units
direkt im Browser an und aktualisiert sie alle fünf Sekunden. Der Zugriff ist
an die Admin-Anmeldung gebunden; es gibt keine frei wählbaren Units oder
Journal-Parameter. Nach dem Dashboard-Update auf 1.11.7 muss
`installer/bootstrap-admin.sh` **einmalig erneut als root** ausgeführt werden,
da der normale Updater die sudoers-Datei absichtlich nicht überschreibt. Erst
dann kann der Dashboard-Benutzer die fest definierten Log-Ausgaben lesen.
Ab 1.11.8 steht über der Ausgabe ein Status für den letzten Lauf: grün bei
erfolgreichem systemd-Abschluss, rot bei fehlgeschlagenem Abschluss und
„Läuft …“ während des Auftrags. Ohne eindeutiges Ergebnis bleibt die Anzeige
neutral.

## Bitcoin Core aktualisieren

Unter `/admin` wird das von `bitcoincore.org` heruntergeladene Linux-Archiv
ausgewählt oder per Drag-and-drop abgelegt. Erlaubt sind ausschließlich stabile
Release-Dateien mit einem dieser Namen:

```text
bitcoin-VERSION-x86_64-linux-gnu.tar.gz
bitcoin-VERSION-aarch64-linux-gnu.tar.gz
```

Das Dashboard akzeptiert höchstens 200 MiB und nur die Architektur des Servers.
Debug-, Quellcode-, Windows-, macOS- und Release-Candidate-Archive werden
abgelehnt. Nach dem Upload zeigt `/admin` Dateiname, Größe und den Anfang des
lokal berechneten SHA-256-Werts. **Geprüft installieren** startet den
parameterlosen Root-Auftrag.

Der Root-Helfer kopiert die hochgeladene Datei zunächst aus
`/var/lib/bitcoin-dashboard/bitcoin-core-upload` in ein root-eigenes temporäres
Verzeichnis. Aus der bereits streng validierten Version baut er ausschließlich
diese beiden URLs:

```text
https://bitcoincore.org/bin/bitcoin-core-VERSION/SHA256SUMS
https://bitcoincore.org/bin/bitcoin-core-VERSION/SHA256SUMS.asc
```

Anschließend werden GPG-Signatur, SHA-256, Archivpfade, Plattform und Version
geprüft. Eine bereits installierte oder ältere Version wird abgelehnt. Erst
danach stoppt der Helfer bitcoind, sichert `/home/btc/bin`, installiert die
Binärdateien und startet den Dienst. Ein Startfehler stellt das Backup wieder
her. Nach Erfolg werden Upload und Metadaten entfernt.

Ein manuell vorbereitetes Bitcoin-Core-Paket kann weiterhin unter
`/var/cache/bitcoin-dashboard-updates/bitcoin-core-update` bereitgestellt
werden; im normalen Betrieb ist der Upload über `/admin` vorgesehen.

### Reverse Proxy für den Upload

Für Plesk muss `plesk-apache.conf` wegen der längeren Zeitbegrenzung erneut in
die zusätzlichen Apache-Direktiven übernommen werden. Der Inhalt von
`plesk-nginx.conf` gehört in **Additional nginx directives**. Er setzt das
Uploadlimit auf 200 MB und deaktiviert die vollständige nginx-Zwischenpufferung.

### Vertrauenswürdige Signaturschlüssel

Der Updater benötigt:

```text
/usr/local/share/bitcoin-core/trustedkeys.gpg
```

Mindestens zwei unterschiedliche gültige Signaturen aus diesem Schlüsselbund
sind erforderlich. Der Grenzwert steht als `BITCOIN_MIN_VALID_SIGNATURES=2` in
`/etc/bitcoin-dashboard-updater.conf` und sollte nicht ohne bewusste
Risikoabwägung reduziert werden.

Schlüssel können aus dem offiziellen Repository `bitcoin-core/guix.sigs` bezogen
werden. Sie dürfen jedoch erst importiert werden, nachdem der jeweilige
Fingerprint über eine unabhängige, vertrauenswürdige Quelle geprüft wurde:

```bash
keywork=$(mktemp -d)
git clone --depth 1 https://github.com/bitcoin-core/guix.sigs.git \
  "$keywork/guix.sigs"
gpg --show-keys --with-fingerprint \
  "$keywork"/guix.sigs/builder-keys/*.gpg
```

Erst nach dem Vergleich der Fingerprints mindestens zweier bewusst ausgewählter
Signer werden deren Schlüssel importiert:

```bash
sudo install -d -o root -g root -m 0755 /usr/local/share/bitcoin-core
sudo gpg --batch --no-default-keyring \
  --keyring /usr/local/share/bitcoin-core/trustedkeys.gpg \
  --import /PFAD/ZU/SIGNER-1.gpg /PFAD/ZU/SIGNER-2.gpg
sudo chmod 0644 /usr/local/share/bitcoin-core/trustedkeys.gpg
rm -rf -- "$keywork"
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

Die Datei muss `root:root` gehören und darf nicht durch `btc` beziehungsweise
den gewählten Dashboard-Benutzer beschreibbar sein. Die Sudoers-Regel erlaubt
ausschließlich zwei vollständig festgelegte `systemd-run`-Aufrufe ohne variable
Argumente. Dadurch laufen Updates außerhalb der Dashboard-Control-Group und ein
Dashboard-Update kann den aufrufenden Webprozess gefahrlos neu starten.

```text
/usr/bin/systemd-run --unit=bitcoin-dashboard-update --collect --no-block /usr/local/sbin/update-bitcoin-dashboard
/usr/bin/systemd-run --unit=bitcoin-core-update --collect --no-block /usr/local/sbin/update-bitcoin-core
```

Das GitHub-Token darf niemals in Git, Logs oder Release-Paketen gespeichert
werden. Nach einer unbeabsichtigten Offenlegung muss es bei GitHub sofort
widerrufen werden.

## Fine-grained GitHub-Token einrichten

Die Token-Verwaltung befindet sich unter
<https://github.com/settings/personal-access-tokens>. Dort **Generate new
token** auswählen und diese Werte verwenden:

| Einstellung | Wert |
|---|---|
| Token name | `Bitcoin Dashboard Server` |
| Expiration | beispielsweise 365 Tage |
| Resource owner | `todo1971` |
| Repository access | `Only select repositories` |
| Repository | `bitcoin-node-dashboard` |
| Repository permission | ausschließlich `Contents: Read-only` |

`Metadata: Read-only` wird von GitHub automatisch ergänzt. Schreibrechte,
Actions-, Administration- oder Kontoberechtigungen sind nicht erforderlich.
Das Token wird nach dem Erzeugen nur einmal vollständig angezeigt. Es darf
nicht in Chat, Shell-History, Git oder Dokumentation kopiert werden.

Auf dem Server wird es mit einem Editor direkt in die Root-Konfiguration
geschrieben:

```bash
sudoedit /etc/default/bitcoin-dashboard
```

```text
DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard
DASHBOARD_GITHUB_TOKEN=github_pat_HIER_DAS_ECHTE_TOKEN
```

Das Beispiel `github_pat_HIER_DAS_ECHTE_TOKEN` muss vollständig durch das von
GitHub ausgegebene Token ersetzt werden. Anschließend Rechte setzen und Dienst
neu starten:

```bash
sudo chown root:root /etc/default/bitcoin-dashboard
sudo chmod 0640 /etc/default/bitcoin-dashboard
sudo systemctl restart bitcoin-dashboard
```

Ob ein Wert vorhanden ist, lässt sich prüfen, ohne das Geheimnis auszugeben:

```bash
sudo awk -F= '
  /^DASHBOARD_GITHUB_TOKEN=/ {
    print length($2) >= 20 ? "GitHub-Token ist gesetzt" : "GitHub-Token fehlt"
  }
' /etc/default/bitcoin-dashboard
```

Danach zeigt `/admin` beispielsweise
`Installiert: 1.11.8 · GitHub: 1.11.8 · aktuell`. Schlägt die Prüfung fehl,
helfen die Logs:

```bash
sudo journalctl -u bitcoin-dashboard -n 50 --no-pager
```

Vor Ablauf wird ein neues Token mit denselben Minimalrechten erzeugt, der Wert
in `/etc/default/bitcoin-dashboard` ersetzt und der Dienst neu gestartet. Das
alte Token danach bei GitHub widerrufen. Bei vermuteter Offenlegung ist es
sofort zu widerrufen und zu ersetzen.
