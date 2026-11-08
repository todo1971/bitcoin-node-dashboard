#!/usr/bin/python3 -I
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
"""Install protected dashboard code and separate local Core RPC privileges."""
import hashlib
import hmac
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
import pwd
import grp

PROJECT = Path(__file__).resolve().parent.parent
STATE = Path("/var/lib/bitcoin-dashboard")
TARGET = Path("/opt/bitcoin-dashboard")
CONFIG = Path("/etc/bitcoin-dashboard-updater.conf")
SERVICE = Path("/etc/systemd/system/bitcoin-dashboard.service")
METHODS = ("getblockchaininfo", "getnetworkinfo", "getmempoolinfo", "getnettotals",
           "getpeerinfo", "uptime", "getblockstats", "getrawmempool", "getchaintips",
           "gettxoutsetinfo", "getblockcount", "estimatesmartfee")


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def regular_bytes(path, require_root=False):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("An absolute file path is required")
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:-1]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = following
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as incoming:
            info = os.fstat(incoming.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 250_000_000:
                raise ValueError("Unexpected file type or size")
            if require_root and (info.st_uid != 0 or info.st_mode & 0o022):
                raise ValueError("Core binaries must be root-owned and protected")
            return incoming.read()
    finally:
        os.close(directory)


def settings(path):
    if not path.exists():
        return {}
    if path.is_symlink():
        raise ValueError(f"Refusing configuration link: {path}")
    values = {}
    for line in regular_bytes(path).decode("utf-8").splitlines():
        if re.match(r"^[A-Z][A-Z0-9_]*=", line):
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    return values


def atomic_write(path, content, mode=0o600, uid=0, gid=0):
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".dashboard.")
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content.encode() if isinstance(content, str) else content)
            output.flush()
            os.fsync(output.fileno())
        os.chown(temporary, uid, gid)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def reject_links(path):
    for root, directories, files in os.walk(path, followlinks=False):
        for name in directories + files:
            entry = Path(root) / name
            if entry.is_symlink() or not (entry.is_dir() or entry.is_file()):
                raise ValueError(f"Unexpected link or special file: {entry}")


def ownership(path):
    result={}
    for root, directories, files in os.walk(path, followlinks=False):
        for entry in [Path(root),*(Path(root)/name for name in directories+files)]:
            info=entry.lstat()
            result[str(entry.relative_to(path))]=(info.st_uid,info.st_gid)
    return result


def restore_ownership(path, owners):
    for relative,(uid,gid) in owners.items():
        os.chown(path/relative,uid,gid,follow_symlinks=False)


def install():
    if os.geteuid() != 0:
        raise ValueError("Run as root from a verified release")
    os.umask(0o077)
    source_guard=str(PROJECT/"installer/update_guard.py")
    run("/usr/bin/python3","-I",source_guard,"check","/opt","/var/lib","/usr/local")
    # The supplied source is the release explicitly selected by the root operator.
    for destination in (Path("/usr/local/libexec"), Path("/usr/local/sbin")):
        if destination.exists():
            run("/usr/bin/python3","-I",source_guard,"check",str(destination))
        destination.mkdir(exist_ok=True)
        destination.chmod(0o755)
    helpers = (
        ("update_guard.py", "/usr/local/libexec/bitcoin-dashboard-update-guard"),
        ("fetch-dashboard-release", "/usr/local/libexec/fetch-bitcoin-dashboard-release"),
        ("update-bitcoin-dashboard", "/usr/local/sbin/update-bitcoin-dashboard"),
        ("update-bitcoin-core", "/usr/local/sbin/update-bitcoin-core"),
    )
    guard = "/usr/local/libexec/bitcoin-dashboard-update-guard"
    if CONFIG.exists() or CONFIG.is_symlink():
        run("/usr/bin/python3", "-I", str(PROJECT/"installer/update_guard.py"), "check", str(CONFIG))
    config = settings(CONFIG)
    environment = settings(STATE/".env")
    if not environment:
        environment = settings(Path("/etc/default/bitcoin-dashboard"))
    if not environment:
        environment = settings(PROJECT/"bitcoin-dashboard.env.example")
    unit_text = run("systemctl", "cat", "bitcoind.service") if subprocess.run(
        ["systemctl", "cat", "bitcoind.service"], capture_output=True).returncode == 0 else ""
    starts = re.findall(r"^ExecStart=(.+)$", unit_text, re.M)
    core_command = shlex.split(starts[-1]) if starts else []
    core_user = run("systemctl", "show", "bitcoind", "-p", "User", "--value") if starts else ""
    name = config.get("DASHBOARD_USER", "bitcoin-dashboard")
    if name in ("root", core_user, "btc"):
        name = "bitcoin-dashboard"
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", name):
        raise ValueError("Invalid dashboard account")
    try:
        account = pwd.getpwnam(name)
    except KeyError:
        run("useradd", "--system", "--user-group", "--home-dir", str(STATE),
            "--no-create-home", "--shell", "/usr/sbin/nologin", name)
        account = pwd.getpwnam(name)
    if account.pw_uid == 0 or core_user and account.pw_uid == pwd.getpwnam(core_user).pw_uid:
        raise ValueError("Dashboard requires a separate unprivileged account")
    if STATE.is_symlink() or TARGET.is_symlink():
        raise ValueError("Unsafe installation link")
    for path in (STATE, TARGET):
        if path.exists():
            # The root-owned application may contain the documented .env link.
            if path == STATE:
                reject_links(path)
    backup_parent=Path("/var/backups/bitcoin-dashboard")
    run("/usr/bin/python3","-I",source_guard,"check",str(backup_parent if backup_parent.exists() else backup_parent.parent))
    backup_parent.mkdir(exist_ok=True,mode=0o700)
    backup=Path(tempfile.mkdtemp(prefix="hardening-"+time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())+"-",dir=backup_parent))
    tracked = [SERVICE, CONFIG]
    tracked.extend(Path(destination) for _,destination in helpers)
    old_code = backup/"code"
    code_owners = ownership(TARGET) if TARGET.exists() else {}
    if TARGET.exists():
        shutil.copytree(TARGET, old_code, symlinks=True)
    was_running = subprocess.run(["systemctl","is-active","--quiet","bitcoin-dashboard"]).returncode == 0
    state_backup = backup/"state"
    state_owners = ownership(STATE) if STATE.exists() else {}
    for path in tracked:
        if path.exists():
            run("/usr/bin/python3","-I",source_guard,"check",str(path))
            shutil.copy2(path, backup/(path.parent.name+"-"+path.name))
    core_dropin = Path("/etc/systemd/system/bitcoind.service.d/bitcoin-dashboard-hardening.conf")
    core_config = Path("/etc/bitcoin-dashboard/bitcoin.conf")
    core_metadata = {}
    for path in (core_dropin, core_config):
        if path.exists():
            info=path.stat()
            core_metadata[path]=(stat.S_IMODE(info.st_mode),info.st_uid,info.st_gid)
            shutil.copy2(path, backup/("core-"+path.name))
    stage = Path(tempfile.mkdtemp(prefix=".bitcoin-dashboard-stage.", dir="/opt"))
    core_changed = False
    try:
        # A partial backup must never replace live state during rollback.
        if was_running or SERVICE.exists():
            run("systemctl", "stop", "bitcoin-dashboard.service")
        if STATE.exists():
            partial_state = backup/"state-incomplete"
            shutil.copytree(STATE, partial_state)
            os.replace(partial_state, state_backup)
            import json
            atomic_write(backup/"state-owners.json",json.dumps(state_owners))
        for source, destination in helpers:
            atomic_write(Path(destination), (PROJECT/"installer"/source).read_bytes(), 0o755)
        for entry in PROJECT.iterdir():
            if entry.name.startswith(".") or entry.name.startswith("preview") or entry.name == "__pycache__":
                continue
            if entry.is_symlink():
                raise ValueError("Release source contains a link")
            if entry.is_dir():
                shutil.copytree(entry, stage/entry.name)
            else:
                shutil.copy2(entry, stage/entry.name)
        reject_links(stage)
        for root, directories, files in os.walk(stage):
            os.chmod(root, 0o755)
            for filename in files:
                path = Path(root)/filename
                path.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)
        if TARGET.exists():
            shutil.rmtree(TARGET)
        os.replace(stage, TARGET)
        STATE.mkdir(exist_ok=True)
        os.chown(STATE, account.pw_uid, account.pw_gid)
        STATE.chmod(0o750)
        for root, directories, files in os.walk(STATE):
            os.chown(root, account.pw_uid, account.pw_gid)
            for filename in files:
                path = Path(root)/filename
                os.chown(path, account.pw_uid, account.pw_gid)
        (TARGET/".env").symlink_to(STATE/".env")
        if not environment.get("ADMIN_TOKEN") or len(environment["ADMIN_TOKEN"]) < 32:
            environment["ADMIN_TOKEN"] = secrets.token_urlsafe(32)
        if core_command and config.get("LOCAL_RPC_HARDENED") != "1":
            original_conf = next((arg.split("=",1)[1] for arg in core_command if arg.startswith("-conf=")), None)
            if not original_conf or not core_user:
                raise ValueError("Local Core requires an explicit config path and service user")
            text = regular_bytes(Path(original_conf)).decode("utf-8")
            text = re.sub(r"\n# dashboard-rpc-start\n.*?# dashboard-rpc-end\n", "\n", text, flags=re.S)
            password, salt = secrets.token_urlsafe(32), secrets.token_hex(16)
            digest = hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()
            text += "\n# dashboard-rpc-start\n" + (
                f"rpcauth=dashboard-monitor:{salt}$"+digest+"\n"
                "rpcwhitelistdefault=0\n"
                "rpcwhitelist=dashboard-monitor:"+",".join(METHODS)+"\n# dashboard-rpc-end\n")
            core_account = pwd.getpwnam(core_user)
            core_config.parent.mkdir(exist_ok=True)
            os.chown(core_config.parent, 0, core_account.pw_gid)
            core_config.parent.chmod(0o750)
            atomic_write(core_config, text, 0o640, 0, core_account.pw_gid)
            binary_dir = Path("/usr/local/lib/bitcoin-core/bin")
            for directory in (binary_dir.parent, binary_dir):
                if directory.exists():
                    run("/usr/bin/python3", "-I", guard, "check", str(directory))
                directory.mkdir(exist_ok=True)
                directory.chmod(0o755)
            run("/usr/bin/python3", "-I", guard, "check", str(binary_dir))
            for binary in Path(core_command[0]).parent.iterdir():
                if not (binary.name == "bitcoind" or binary.name.startswith("bitcoin-")):
                    continue
                atomic_write(binary_dir/binary.name, regular_bytes(binary, require_root=True), 0o755)
            core_command[0] = str(binary_dir/"bitcoind")
            core_command = [f"-conf={core_config}" if arg.startswith("-conf=") else arg for arg in core_command]
            core_dropin.parent.mkdir(exist_ok=True)
            atomic_write(core_dropin, "[Service]\nExecStart=\nExecStart="+shlex.join(core_command)+"\n", 0o644)
            core_changed = True
            rpc_port = re.search(r"^rpcport=(\d+)$", text, re.M)
            environment.update(BITCOIN_RPC_URL="http://127.0.0.1:"+ (rpc_port[1] if rpc_port else "8332"),
                               BITCOIN_COOKIE=str(STATE/"rpc.auth"), BITCOIN_CLI=str(binary_dir/"bitcoin-cli"))
            atomic_write(STATE/"rpc.auth", "dashboard-monitor:"+password+"\n", 0o600, account.pw_uid, account.pw_gid)
            config["BITCOIN_BIN_DIR"] = str(binary_dir)
            config["BITCOIN_RPC_ACCESS_FILE"] = str(STATE/"rpc.auth")
            config["BITCOIN_RPC_URL"] = environment["BITCOIN_RPC_URL"]
            config["LOCAL_RPC_HARDENED"] = "1"
            actual_datadir = next((arg.split("=",1)[1] for arg in core_command if arg.startswith("-datadir=")),
                                  environment.get("BITCOIN_DATADIR","/home/btc/bitcoin-data"))
            environment["BITCOIN_DATADIR"] = actual_datadir
            config["BITCOIN_DATADIR"] = actual_datadir
        elif not core_command:
            credentials=regular_bytes(Path(environment["BITCOIN_COOKIE"]))
            atomic_write(STATE/"rpc.auth",credentials,0o600,account.pw_uid,account.pw_gid)
            environment["BITCOIN_COOKIE"]=str(STATE/"rpc.auth")
        disk_path = environment.get("BITCOIN_DATADIR", "/")
        environment["DISK_MONITOR_PATH"] = run("df", "--output=target", "--", disk_path).splitlines()[-1].strip()
        atomic_write(STATE/".env", "".join(f"{key}={value}\n" for key,value in environment.items()), 0o600, account.pw_uid, account.pw_gid)
        unit = (PROJECT/"bitcoin-dashboard.service").read_text()
        unit = unit.replace("User=bitcoin-dashboard", f"User={name}").replace("Group=bitcoin-dashboard", f"Group={grp.getgrgid(account.pw_gid).gr_name}")
        atomic_write(SERVICE, unit, 0o644)
        config.update(UPDATE_ROOT="/var/cache/bitcoin-dashboard-updates", DASHBOARD_USER=name,
                      DASHBOARD_TARGET=str(TARGET), DASHBOARD_SERVICE="bitcoin-dashboard",
                      DASHBOARD_HEALTH_URL="http://127.0.0.1:"+environment.get("DASHBOARD_PORT","8787")+"/healthz")
        config.setdefault("DASHBOARD_GITHUB_REPOSITORY","todo1971/bitcoin-node-dashboard")
        config.setdefault("BITCOIN_SERVICE","bitcoind")
        config.setdefault("BITCOIN_MIN_VALID_SIGNATURES","2")
        config.setdefault("BITCOIN_UPLOAD_DIR",str(STATE/"bitcoin-core-upload"))
        config.setdefault("BITCOIN_DATADIR",environment.get("BITCOIN_DATADIR","/home/btc/bitcoin-data"))
        config.setdefault("BITCOIN_COOKIE","/home/btc/bitcoin-core/.bitcoin/.cookie")
        atomic_write(CONFIG,"".join(f"{key}={shlex.quote(value)}\n" for key,value in config.items()))
        cache = Path(config["UPDATE_ROOT"])
        cache.mkdir(exist_ok=True, mode=0o700)
        run("/usr/bin/python3", "-I", guard, "check", str(cache), str(TARGET), str(CONFIG))
        backup.parent.chmod(0o700)
        sudoers = (PROJECT/"installer"/"sudoers.template").read_text().replace("@USER@",name)
        sudo_file = Path("/etc/sudoers.d/bitcoin-dashboard-updates")
        tracked.append(sudo_file)
        if sudo_file.exists():
            shutil.copy2(sudo_file, backup/(sudo_file.parent.name+"-"+sudo_file.name))
        atomic_write(sudo_file,sudoers,0o440)
        run("visudo","-cf",str(sudo_file))
        run("systemctl","daemon-reload")
        if core_changed:
            run("systemctl","restart","bitcoind")
        run("systemctl","restart","bitcoin-dashboard")
        import urllib.request
        for attempt in range(60):
            try:
                with urllib.request.urlopen(config["DASHBOARD_HEALTH_URL"],timeout=3):
                    break
            except OSError:
                if attempt == 59:
                    raise ValueError("Dashboard health check failed after migration")
                time.sleep(2)
        print("Dashboard hardening installed. Backup: "+str(backup))
    except Exception:
        subprocess.run(["systemctl","stop","bitcoin-dashboard"],capture_output=True)
        for path in tracked:
            saved=backup/(path.parent.name+"-"+path.name)
            if saved.exists():
                mode=0o440 if path.parent.name=="sudoers.d" else 0o755 if path.parent.name in ("sbin","libexec") else 0o600
                atomic_write(path,saved.read_bytes(),mode)
            elif path.exists():
                path.unlink()
        for path in (core_dropin, core_config):
            saved=backup/("core-"+path.name)
            if saved.exists():
                mode,uid,gid=core_metadata[path]
                atomic_write(path,saved.read_bytes(),mode,uid,gid)
            elif path.exists():
                path.unlink()
        if old_code.exists():
            shutil.rmtree(TARGET)
            shutil.copytree(old_code,TARGET,symlinks=True)
            restore_ownership(TARGET,code_owners)
        if state_backup.exists():
            shutil.rmtree(STATE)
            shutil.copytree(state_backup,STATE)
            restore_ownership(STATE,state_owners)
        subprocess.run(["systemctl","daemon-reload"],capture_output=True)
        if core_changed:
            subprocess.run(["systemctl","restart","bitcoind"],capture_output=True)
        if was_running:
            subprocess.run(["systemctl","start","bitcoin-dashboard"],capture_output=True)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == "__main__":
    try:
        install()
    except Exception as error:
        import traceback
        location=traceback.extract_tb(error.__traceback__)[-1]
        raise SystemExit("Hardening failed. Review the protected backup and service state. "
                         +type(error).__name__+" at "+Path(location.filename).name+":"+str(location.lineno))
