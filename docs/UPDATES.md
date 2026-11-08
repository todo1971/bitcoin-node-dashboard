# Sichere Updates

Deutsch | [English](en/UPDATES.md)

## Einmalige Sicherheitsmigration

Vor dem ersten Update mit den neuen Helfern die [Migration ab 1.24](SECURITY.md) ausführen. Der normale Updater ersetzt keine Root-Helfer, Units oder Sudoers-Regeln. Bestehende Installationen dürfen diesen Schritt nicht überspringen.

## Dashboard aktualisieren und Quelle festlegen

`/admin` zeigt verfügbare Version, Ergebnis und letzte Journalzeilen. Der Browser startet ausschließlich festgelegte Root-Aufträge ohne variable Argumente. Manuell aktualisieren und die Quelle lokal verwalten:

```bash
sudo /usr/local/sbin/update-bitcoin-dashboard
sudo journalctl -u bitcoin-dashboard-update -n 80 --no-pager
```

```bash
sudoedit /etc/bitcoin-dashboard-updater.conf
```

```text
DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard
DASHBOARD_GITHUB_TOKEN=
```

Das öffentliche Repository benötigt keinen Token. Root liest Repository und optionales Token ausschließlich aus dieser root-eigenen Datei (0600), niemals aus der Dashboard-`.env`. Die Weboberfläche kann diese Quelle nicht ändern. Die separate unprivilegierte Versionsanzeige kann weiterhin Werte aus der `.env` verwenden. Änderungen der Root-Konfiguration benötigen keinen Dienstneustart.

Bei privaten Forks ein Fine-grained Token unter [GitHub](https://github.com/settings/personal-access-tokens) anlegen: genau ein Repository und ausschließlich `Contents: Read-only`. Nur lokal eintragen, niemals in Git, Chat oder Logs. Bei Offenlegung sofort widerrufen.

Der Helfer sperrt parallele Updates, lädt die beiden versionierten Release-Assets, prüft SHA-256 und alle Archivmitglieder vor dem Entpacken und testet unprivilegiert. Anschließend sichert und ersetzt er den geschützten Programmbaum, startet das Dashboard neu und prüft `/healthz`. Bei Fehlern wird der alte Baum wiederhergestellt und sein Start versucht. Root importiert keinen Anwendungscode. Backups: `/var/backups/bitcoin-dashboard`; root-eigener Downloadcache: `/var/cache/bitcoin-dashboard-updates`.

Erforderliche Assets: `bitcoin-node-dashboard-VERSION.tar.gz` und `bitcoin-node-dashboard-VERSION.tar.gz.sha256`. GitHubs automatische Quellcodearchive ersetzen sie nicht. Eine Prüfsumme aus demselben Release schützt nicht gegen einen kompromittierten Herausgeberaccount. Öffentliche API-Abfragen unterliegen GitHubs Ratenlimit; die Versionsanzeige verwendet einen Cache.

## Bitcoin Core aktualisieren

Unter `/admin` ein offizielles stabiles Linux-Archiv hochladen: `bitcoin-VERSION-x86_64-linux-gnu.tar.gz` oder `bitcoin-VERSION-aarch64-linux-gnu.tar.gz`. Nur die Serverarchitektur und höchstens 200 MiB sind erlaubt. Debug-, Quellcode-, Windows-, macOS- und Vorabpakete werden abgewiesen.

Der parameterlose Root-Auftrag kopiert Uploads ohne Symlink-Folgen in geschützten Speicher. Er lädt `SHA256SUMS` und `SHA256SUMS.asc` ausschließlich von der offiziellen versionsgebundenen Bitcoin-Core-Adresse. Mindestens zwei unterschiedliche gültige Signaturen aus `/usr/local/share/bitcoin-core/trustedkeys.gpg`, SHA-256, Archivpfade, Plattform und Version müssen passen. Gleiche und ältere Versionen werden abgewiesen.

Signaturschlüssel aus dem offiziellen Repository `bitcoin-core/guix.sigs` erst nach unabhängigem Vergleich ihrer Fingerprints in den root-eigenen Keyring importieren. `BITCOIN_MIN_VALID_SIGNATURES=2` nicht ohne bewusste Risikoabwägung reduzieren. Token und private Schlüssel gehören niemals in Pakete.

Nach der Migration stehen Programme unter `/usr/local/lib/bitcoin-core/bin`. Der Helfer stoppt Core, sichert und ersetzt Programme, startet Core und prüft RPC mit eingeschränkten Zugangsdaten. Startfehler lösen die Wiederherstellung aus. Major-Releases vorab auf Konfigurations-, Wallet- und Datenbankänderungen prüfen. Keine unbeaufsichtigten automatischen Core-Updates. Externe Nodes und Container auf ihrem jeweiligen Host beziehungsweise durch Image-Austausch aktualisieren.

## Proxy und Fehlerdiagnose

Uploadlimits und Zeitgrenzen des Reverse Proxys anpassen. `plesk-apache.conf` gehört zu Apache, `plesk-nginx.conf` nur zu tatsächlich eingesetztem nginx. Adminanmeldung über HTTPS oder SSH-Tunnel. Port 8787 und RPC niemals öffentlich freigeben.

Bei Fehlern getrennte Update-Logs im Adminbereich, Dienstzustand und geschützte Backups prüfen. [Sicherheitsmodell und Testumfang](SECURITY.md).
