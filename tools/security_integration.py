#!/usr/bin/python3
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
"""Run only in a disposable root container, never on a production host."""
import base64
import json
import os
import pwd
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/run/dashboard-security-test")
SOURCE = Path("/source")


def control(arguments):
    verb=arguments[0]
    name=next((arg.removesuffix(".service") for arg in arguments[1:] if not arg.startswith("-")), "")
    if verb=="daemon-reload":
        return 0
    unit=Path("/etc/systemd/system")/(name+".service")
    if verb=="cat":
        if not unit.exists():
            return 1
        print(unit.read_text())
        dropin=Path(str(unit)+".d/bitcoin-dashboard-hardening.conf")
        if dropin.exists():
            print(dropin.read_text())
        return 0
    if verb=="show":
        print("btc")
        return 0
    pidfile=ROOT/(name+".pid")
    if verb in ("stop","restart"):
        if pidfile.exists():
            pid=int(pidfile.read_text())
            try:
                os.killpg(pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            time.sleep(2)
            pidfile.unlink()
        if verb=="stop":
            return 0
    if verb=="is-active":
        return 0 if pidfile.exists() else 3
    if verb in ("start","restart"):
        fail=ROOT/"fail-dashboard-once"
        if name=="bitcoin-dashboard" and fail.exists():
            fail.unlink()
            return 1
        result=subprocess.check_output(["/usr/bin/systemctl","cat",name],text=True)
        lines=result.splitlines()
        command=[line.split("=",1)[1] for line in lines if line.startswith("ExecStart=") and line!="ExecStart="][-1]
        account=[line.split("=",1)[1] for line in lines if line.startswith("User=")][-1]
        environment=os.environ.copy()
        for line in lines:
            if line.startswith("EnvironmentFile="):
                for assignment in Path(line.split("=",1)[1]).read_text().splitlines():
                    if "=" in assignment and not assignment.startswith("#"):
                        key,value=assignment.split("=",1)
                        environment[key]=value
        with (ROOT/(name+".log")).open("ab") as log:
            process=subprocess.Popen(["runuser","-u",account,"--",*shlex.split(command)],
                env=environment,stdout=log,stderr=log,start_new_session=True,cwd="/")
        pidfile.write_text(str(process.pid))
        return 0
    return 0


def execute(*arguments):
    subprocess.run(arguments,check=True,capture_output=True)


def wait_health():
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8787/healthz",timeout=2) as response:
                assert response.status==200
            return
        except OSError:
            time.sleep(1)
    raise AssertionError("Dashboard health did not recover")


def test():
    assert os.environ.get("DISPOSABLE_SECURITY_CONTAINER")=="1", "Disposable container required"
    ROOT.mkdir(mode=0o700)
    unitdir=Path("/etc/systemd/system")
    unitdir.mkdir(parents=True,exist_ok=True)
    controller=Path("/usr/bin/systemctl")
    controller.write_text("#!/usr/bin/python3\nimport runpy,sys\n"
        "module=runpy.run_path('/source/tools/security_integration.py',run_name='fixture_module')\n"
        "raise SystemExit(module['control'](sys.argv[1:]))\n")
    controller.chmod(0o755)
    execute("useradd","--create-home","--shell","/usr/sbin/nologin","btc")
    account=pwd.getpwnam("btc")
    binaries=Path("/home/btc/bin")
    binaries.mkdir()
    for binary in Path(os.environ["BITCOIN_TEST_BIN"]).iterdir():
        if binary.is_file():
            shutil.copy2(binary,binaries/binary.name)
    data=Path("/home/btc/bitcoin-data")
    data.mkdir()
    os.chown(data,account.pw_uid,account.pw_gid)
    configuration=Path("/home/btc/bitcoin.conf")
    configuration.write_text("regtest=1\nserver=1\nlisten=0\n[regtest]\nrpcport=18443\nrpcbind=127.0.0.1\nrpcallowip=127.0.0.1\n")
    os.chown(configuration,account.pw_uid,account.pw_gid)
    core_unit=unitdir/"bitcoind.service"
    core_unit.write_text("[Service]\nUser=btc\nExecStart=/home/btc/bin/bitcoind -conf=/home/btc/bitcoin.conf -datadir=/home/btc/bitcoin-data -daemon=0\n")
    state=Path("/var/lib/bitcoin-dashboard")
    state.mkdir()
    os.chown(state,account.pw_uid,account.pw_gid)
    environment=state/".env"
    environment.write_text("DASHBOARD_PORT=8787\nBITCOIN_CLI=/home/btc/bin/bitcoin-cli\n"
        "BITCOIN_DATADIR=/home/btc/bitcoin-data\nBITCOIN_COOKIE=/home/btc/bitcoin-data/regtest/.cookie\n"
        "DATABASE_PATH=/var/lib/bitcoin-dashboard/history.sqlite3\nADMIN_TOKEN="+"x"*40+"\n"
        "DASHBOARD_GITHUB_REPOSITORY=untrusted/source\n")
    os.chown(environment,account.pw_uid,account.pw_gid)
    environment.chmod(0o600)
    old_target=Path("/home/btc/bitcoin-dashboard")
    old_target.mkdir()
    os.chown(old_target,account.pw_uid,account.pw_gid)
    unitdir.joinpath("bitcoin-dashboard.service").write_text("[Service]\nUser=btc\n"
        "EnvironmentFile=/var/lib/bitcoin-dashboard/.env\nExecStart=/usr/bin/python3 "+str(SOURCE/"app.py")+"\n")
    execute("/usr/bin/systemctl","start","bitcoind")
    execute("/usr/bin/systemctl","start","bitcoin-dashboard")
    wait_health()
    execute("/bin/sh",str(SOURCE/"installer/bootstrap-admin.sh"))
    wait_health()
    dashboard=pwd.getpwnam("bitcoin-dashboard")
    assert dashboard.pw_uid != account.pw_uid
    assert environment.stat().st_uid==dashboard.pw_uid
    assert Path("/opt/bitcoin-dashboard/app.py").stat().st_uid==0
    assert "DASHBOARD_GITHUB_REPOSITORY=todo1971/bitcoin-node-dashboard" in Path("/etc/bitcoin-dashboard-updater.conf").read_text()
    denied=subprocess.run(["runuser","-u","bitcoin-dashboard","--","test","-r",str(data/"regtest/.cookie")])
    assert denied.returncode != 0
    denied=subprocess.run(["runuser","-u","bitcoin-dashboard","--","test","-w","/opt/bitcoin-dashboard/app.py"])
    assert denied.returncode != 0
    credentials=state.joinpath("rpc.auth").read_bytes().strip()
    authorization="Basic "+base64.b64encode(credentials).decode()
    def rpc(method):
        request=urllib.request.Request("http://127.0.0.1:18443",data=json.dumps(
            {"jsonrpc":"2.0","id":"test","method":method,"params":[]}).encode(),
            headers={"Authorization":authorization,"Content-Type":"application/json"})
        return urllib.request.urlopen(request,timeout=5)
    with rpc("getblockchaininfo") as response:
        assert json.load(response)["result"]["chain"]=="regtest"
    try:
        rpc("getrpcinfo")
        raise AssertionError("RPC allowlist was not enforced")
    except urllib.error.HTTPError as error:
        assert error.code==403
        error.close()
    execute("/usr/bin/python3","-I","/usr/local/libexec/bitcoin-dashboard-update-guard",
            "check","/opt/bitcoin-dashboard","/usr/local/lib/bitcoin-core/bin")
    # A failed second installation must preserve the working state and credentials.
    marker=state/"sentinel"
    marker.write_text("keep")
    os.chown(marker,dashboard.pw_uid,dashboard.pw_gid)
    ROOT.joinpath("fail-dashboard-once").touch()
    failed=subprocess.run(["/bin/sh",str(SOURCE/"installer/bootstrap-admin.sh")],capture_output=True)
    assert failed.returncode != 0
    wait_health()
    assert marker.read_text()=="keep" and marker.stat().st_uid==dashboard.pw_uid
    assert state.joinpath("rpc.auth").read_bytes().strip()==credentials
    print("Root integration passed: real Core regtest RPC allowlist, account separation, protected paths, preserved state and rollback.")


if __name__=="__main__":
    if Path(sys.argv[0]).name=="systemctl":
        raise SystemExit(control(sys.argv[1:]))
    test()
