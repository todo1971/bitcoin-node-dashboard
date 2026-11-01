# All-in-one shell installation

[Deutsch](../SHELL_DOCKER.md) | [English documentation](../../README.en.md#documentation)

The installer copies only the files required for the all-in-one stack to
`/opt/bitcoin-node-dashboard`, generates a random admin token on first
installation and validates the Compose file.
Existing systemd services are neither stopped nor changed.

## Prepare without starting

```bash
tmpdir=$(mktemp -d)
tar -xzf bitcoin-node-dashboard-1.21.0.tar.gz -C "$tmpdir"
sudo sh "$tmpdir/bitcoin-dashboard/installer/install-docker-all-in-one.sh" \
  --public-address 203.0.113.10 \
  --prepare-only
sudo rm -rf -- "$tmpdir"
```

Then inspect `/opt/bitcoin-node-dashboard/.env`, Bitcoin configuration and
port usage. `.env` belongs to root and has mode `0600`.

## Direct installation and start

Use only on a new server where ports 8333 and 8787 are free:

```bash
sudo sh installer/install-docker-all-in-one.sh \
  --public-address 203.0.113.10
```

The script aborts on occupied ports. It does not stop an existing node or dashboard.

## Status and logs

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml ps
sudo docker compose --env-file .env -f compose.all-in-one.yaml logs --tail 100
curl -fsS http://127.0.0.1:8787/healthz
```

## Updating

First copy a new release over the installation with `--prepare-only`.
An existing `.env` is preserved. Then:

```bash
cd /opt/bitcoin-node-dashboard
sudo docker compose --env-file .env -f compose.all-in-one.yaml build --pull
sudo docker compose --env-file .env -f compose.all-in-one.yaml up -d
```

The Bitcoin Core version is explicitly selected through `BITCOIN_CORE_VERSION`
in `.env`. Change it only after reviewing the target version.
