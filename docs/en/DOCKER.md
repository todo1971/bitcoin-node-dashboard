# Docker deployment

[Deutsch](../DOCKER.md) | [English documentation](../../README.en.md#documentation)

The repository contains three separate Compose variants. Do not start them
simultaneously.

The all-in-one variant also has a protected [shell installer](SHELL_DOCKER.md)
and a guide for [Plesk without nginx](PLESK_DOCKER.md).

## Monitor an existing host node

`compose.host-node.yaml` targets the existing server. bitcoind stays a systemd
service running as `btc`; only the dashboard moves into a container.
The container uses host networking but still binds only to `127.0.0.1:8787`.
The blockchain directory and RPC cookie are mounted read-only.

The container UID and GID must match the host user:

```bash
id btc
```

Both values are `1010` on the original server. Create configuration:

```bash
cd /home/btc/bitcoin-dashboard
cp docker.env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
sudo editor .env
```

Place the generated token in `ADMIN_TOKEN`. `.gitignore` excludes `.env`.
Do not run the systemd dashboard service concurrently during the switch:

```bash
sudo systemctl disable --now bitcoin-dashboard
sudo install -d -o 1010 -g 1010 -m 0750 /var/lib/bitcoin-dashboard
sudo docker compose --env-file .env -f compose.host-node.yaml build --pull
sudo docker compose --env-file .env -f compose.host-node.yaml up -d
sudo docker compose --env-file .env -f compose.host-node.yaml ps
```

Bitcoin Core must provide RPC at `127.0.0.1:8332`.
Never publish that RPC port through the firewall or reverse proxy.

## All-in-one: node and dashboard in one container

`compose.all-in-one.yaml` is the compact option for a fresh installation.
Bitcoin Core and the dashboard run as the same unprivileged user inside one
container. RPC is available only at `127.0.0.1:8332` inside that container and
is not published. Only P2P port 8333 and the locally bound dashboard port 8787
are exposed.

```bash
cp docker.env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
sudo editor .env
sudo docker compose --env-file .env -f compose.all-in-one.yaml config
sudo docker compose --env-file .env -f compose.all-in-one.yaml up -d --build
sudo docker compose --env-file .env -f compose.all-in-one.yaml ps
```

Bitcoin data and dashboard history share the `node-data` volume but use separate
`/data/bitcoin` and `/data/dashboard` subdirectories.
The combined health check requires working Bitcoin RPC and the dashboard endpoint.
If either process unexpectedly exits, the startup script also stops the other;
Docker then restarts the whole container. bitcoind gets up to three minutes for
an orderly shutdown.

This variant is easier to copy and operate, but Bitcoin Core and the dashboard
cannot be restarted or updated independently.
Never open an existing host data directory from the host process and container
at the same time.

## Complete stack with separate containers

`compose.yaml` starts Bitcoin Core and the dashboard together.
P2P port 8333 is published; RPC port 8332 stays inside the private Compose
network `172.30.0.0/24`. The dashboard authenticates using the cookie from
the shared Bitcoin data volume, mounted read-only into the dashboard.

```bash
cp docker.env.example .env
sudo editor .env
sudo docker compose --env-file .env config
sudo docker compose --env-file .env up -d --build
sudo docker compose --env-file .env ps
```

This variant uses `bitcoin/bitcoin` with a fixed version.
The image itself states that it is not an officially supported production image
from the Bitcoin Core project. Explicitly accept that trust model before use,
or build the image reproducibly in-house and manage it in your own registry.

The default is a pruned node targeting approximately 20 GB with its wallet disabled.
Never open an existing host data directory with both the host process and
a Bitcoin container simultaneously.

## Updates

Containers receive neither `/var/run/docker.sock` nor host systemd or sudo access.
In container mode, `/admin` therefore only displays version status and explains
that updates are managed externally.

Update the dashboard:

```bash
git pull --ff-only
sudo docker compose --env-file .env -f compose.host-node.yaml build --pull
sudo docker compose --env-file .env -f compose.host-node.yaml up -d
```

For the complete stack, deliberately set `BITCOIN_CORE_VERSION` in `.env`
to the verified target version, then:

```bash
sudo docker compose --env-file .env pull bitcoin-core
sudo docker compose --env-file .env up -d bitcoin-core dashboard
```

The all-in-one variant always rebuilds and restarts Bitcoin Core and the dashboard
together:

```bash
git pull --ff-only
sudo docker compose --env-file .env -f compose.all-in-one.yaml build --pull
sudo docker compose --env-file .env -f compose.all-in-one.yaml up -d
```

Do not use automatic updates based on `latest`. Major releases may change
behavior, configuration and data formats.

## Operation and diagnosis

```bash
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env logs --tail 100 dashboard
sudo docker compose --env-file .env logs --tail 100 bitcoin-core
curl -fsS http://127.0.0.1:8787/healthz
```

Persistent data resides in `bitcoin-data` and `dashboard-data`. Back up volumes
separately. `docker compose down` without `-v` preserves them.
`docker compose down -v` deletes them and is not part of normal updates.

For all-in-one, back up the single `node-data` volume instead.
Do not use `down -v` during normal operation there either.
