# Sichere Updates

## Integrierte Administration

Die Wartungsoberfläche ist unter `/admin` in das Dashboard integriert. Sie
verwendet ein zufälliges Passwort mit mindestens 32 Zeichen, HTTP-Basic-
Authentifizierung, einen zusätzlichen CSRF-Token, eine globale Sperre nach fünf
Fehlversuchen sowie Größen-, Methoden- und Origin-Prüfungen.

Die Root-Helfer und das Passwort werden aus dem temporär entpackten, zuvor
geprüften Release-Paket eingerichtet. Unter `/home/todo` bleibt nur das Archiv:

```bash
tmpdir=$(mktemp -d)
sudo tar -xzf /home/todo/bitcoin-node-dashboard-1.6.1.tar.gz -C "$tmpdir"
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
bewusst nicht aus einem Update-Archiv überschrieben.

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

### Geplanter Upload im Adminbereich

Als nächste Ausbaustufe erhält `/admin` eine Dateiauswahl mit Drag-and-drop
für das offizielle Archiv
`bitcoin-VERSION-x86_64-linux-gnu.tar.gz`. Das Archiv wird zunächst ohne
Root-Rechte in einem isolierten Upload-Verzeichnis gespeichert. Anschließend
soll der Server `SHA256SUMS` und `SHA256SUMS.asc` selbst aus dem passenden
Release-Verzeichnis auf `bitcoincore.org` laden.

Vor dem Root-Update werden Dateiname, stabile Versionsnummer, Plattform,
Dateigröße, SHA-256-Prüfsumme und GPG-Signaturen kontrolliert. Downgrades und
Archive für eine andere Plattform werden standardmäßig abgelehnt. Erst nach
einer Bestätigung werden bitcoind gestoppt, die bisherigen Binärdateien
gesichert und das neue Release installiert. Versions-, RPC- und Startprüfung
entscheiden anschließend über Erfolg oder automatischen Rollback.

Bis diese Funktion implementiert und getestet ist, gilt weiterhin das oben
beschriebene manuell vorbereitete Verzeichnis. Ein bloß hochgeladenes,
ungeprüftes Archiv wird niemals als Root installiert.

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
`Installiert: 1.6.1 · GitHub: 1.6.1 · aktuell`. Schlägt die Prüfung fehl,
helfen die Logs:

```bash
sudo journalctl -u bitcoin-dashboard -n 50 --no-pager
```

Vor Ablauf wird ein neues Token mit denselben Minimalrechten erzeugt, der Wert
in `/etc/default/bitcoin-dashboard` ersetzt und der Dienst neu gestartet. Das
alte Token danach bei GitHub widerrufen. Bei vermuteter Offenlegung ist es
sofort zu widerrufen und zu ersetzen.
