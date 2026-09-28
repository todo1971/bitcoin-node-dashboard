# Web-Installation

## Sicherheitsmodell

Der Installer wird nicht über eine öffentliche Domain bereitgestellt. Er bindet
fest an `127.0.0.1:8791`, erzeugt bei jedem Start ein zufälliges Passwort und
wird nur durch einen SSH-Tunnel geöffnet. Nach der Installation wird der Prozess
mit `Strg+C` beendet.

Unterstützt werden systemd-basierte Linux-Systeme mit Python 3.11 oder neuer.
Für die Dashboard-Installation muss Bitcoin Core bereits laufen und der gewählte
Service-Benutzer Zugriff auf dessen RPC-Cookie besitzen.

## Start

Paket aus `/home/todo` in ein temporäres Verzeichnis entpacken:

```bash
tmpdir=$(mktemp -d)
sudo tar -xzf /home/todo/bitcoin-node-dashboard-1.6.1.tar.gz -C "$tmpdir"
sudo python3 "$tmpdir/bitcoin-dashboard/installer/web_installer.py"
```

Der Prozess zeigt Benutzername und ein einmaliges Passwort. In einem zweiten
lokalen Terminal wird der Tunnel geöffnet:

```bash
ssh -L 8791:127.0.0.1:8791 trading-server
```

Danach im lokalen Browser öffnen:

```text
http://127.0.0.1:8791
```

Der Installer prüft Benutzer, Pfade und Zahlenbereiche, installiert den Code in
das Home-Verzeichnis des Service-Benutzers, schreibt die Environment-Datei und
eine gehärtete Systemd-Unit, richtet die abgesicherten Update-Helfer ein und
startet das Dashboard. Das ausgegebene Admin-Passwort gehört zu `/admin`.
Nach Abschluss und Beenden des Installers kann das temporäre Verzeichnis mit
`sudo rm -rf -- "$tmpdir"` entfernt werden.

## Neuer Server mit Bitcoin Core

Für einen neuen, dedizierten Server kann zuerst ein Systembenutzer angelegt werden:

```bash
sudo useradd --system --create-home --home-dir /home/btc \
  --shell /usr/sbin/nologin btc
sudo install -d -o btc -g btc -m 0750 /home/btc/bitcoin-data
sudo install -d -o root -g root -m 0755 /home/btc/bin
```

Die Vorlagen `installer/bitcoin.conf.example` und
`installer/bitcoind.service.example` bilden einen sicheren Ausgangspunkt. Vor
dem Start müssen Pfade, Pruning-Größe und gewünschte Wallet-Funktion geprüft
werden.

Bitcoin-Core-Binärpakete sollten nur von `bitcoincore.org` bezogen und anhand
von `SHA256SUMS` sowie einer bewusst ausgewählten Signatur geprüft werden. Der
mitgelieferte Update-Helfer verweigert Pakete ohne diese Prüfungen.

## Reverse Proxy

Nach erfolgreicher Installation bleibt das Dashboard auf `127.0.0.1`. Für den
öffentlichen Zugriff wird ein HTTPS-Reverse-Proxy eingerichtet. Für Plesk liegt
`plesk-apache.conf` bei. Bei Nginx, Caddy oder Apache ohne Plesk wird lediglich
HTTPS auf den lokalen Dashboard-Port weitergeleitet. Bitcoin-RPC-Port 8332 darf
nicht öffentlich freigegeben werden.
