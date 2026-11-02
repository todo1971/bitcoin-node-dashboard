# All-in-one Docker with Plesk

[Deutsch](../PLESK_DOCKER.md) | [English documentation](../../README.en.md#documentation)

This guide covers only optional container installation.
It does not automatically stop or migrate an existing systemd installation.

## Recommended approach without nginx

On a Plesk server without nginx, install the stack through the shell and have
Apache forward HTTPS to the locally bound dashboard at `127.0.0.1:8787`.
Bitcoin P2P remains directly reachable over TCP 8333; RPC port 8332 is not published.

Extract the archive and prepare without starting:

```bash
tmpdir=$(mktemp -d)
tar -xzf bitcoin-node-dashboard-1.21.3.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/install-docker-all-in-one.sh" \
  --public-address 203.0.113.10 \
  --prepare-only
sudo rm -rf -- "$tmpdir"
```

Files are placed under `/opt/bitcoin-node-dashboard`.
Ports 8333 and 8787 must be free before the first start.
The installer does not stop or change existing services.

Start:

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml up -d --build
sudo docker compose --env-file .env -f compose.all-in-one.yaml ps
```

In Plesk, open **Websites & Domains → Domain → Apache & nginx Settings** and
add `plesk-apache-docker.conf` to the additional Apache directives for both
HTTP and HTTPS. No nginx directives are needed.

Check configuration:

```bash
sudo /usr/local/psa/admin/sbin/httpdmng --reconfigure-domain example.org
sudo apache2ctl configtest
sudo systemctl reload apache2
curl -fsS http://127.0.0.1:8787/healthz
```

## Plesk Docker Stacks

Plesk supports [loading Compose files from a webspace as a stack](https://docs.plesk.com/en-US/obsidian/administrator-guide/plesk-administration/using-docker.75823/).
This stack requires its Dockerfile and other build files, so copy the complete
project to the webspace's private directory first, for example:

```text
/var/www/vhosts/example.org/private/bitcoin-node-dashboard
```

Do not place it in `httpdocs`: `.env`, build files and configuration must not
be served publicly. In the project directory:

```bash
cp docker.env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
sudo editor .env
chmod 600 .env
```

Put the generated token in `ADMIN_TOKEN`. In Plesk, select
`compose.all-in-one.yaml` under **Docker → Stacks → Add Stack → Webspace**.

Plesk Docker proxy rules require a running nginx.
On servers without nginx, use the Apache directives above rather than creating
a Docker proxy rule.

## Operation

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml logs --tail 100
sudo docker compose --env-file .env -f compose.all-in-one.yaml restart
sudo docker compose --env-file .env -f compose.all-in-one.yaml down
```

`down` does not delete the data volume. `down -v` deletes the blockchain and
dashboard history; never use it for normal updates.
