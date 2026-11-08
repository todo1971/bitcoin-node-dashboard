#!/usr/bin/python3 -I
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
"""Validate privileged update paths and extract plain release files safely."""
import argparse
import os
import re
import shutil
import stat
import tarfile
import json
import base64
import urllib.request
try:
    import pwd
except ImportError:
    pwd = None
from pathlib import Path, PurePosixPath


def trusted_path(path: Path) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("An absolute trusted path is required")
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError(f"Untrusted owner, permissions or link: {part}")


def extract_archive(archive: Path, destination: Path, prefix: str, maximum: int) -> None:
    trusted_path(destination)
    with tarfile.open(archive, "r:gz") as source:
        members, names, expanded = [], set(), 0
        for member in source:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or not path.parts
                    or path.parts[0] != prefix or "\\" in member.name
                    or not (member.isfile() or member.isdir()) or path in names):
                raise ValueError("Unsafe or duplicate archive entry")
            names.add(path)
            expanded += member.size
            if expanded > maximum or len(names) > 10000:
                raise ValueError("Archive expansion limit exceeded")
            members.append(member)
        # Validate all entries before creating any release files.
        directories = set()
        for member in members:
            path = destination.joinpath(*PurePosixPath(member.name).parts)
            directories.update(parent for parent in path.parents if parent != destination and destination in parent.parents)
            if member.isdir():
                directories.add(path)
        for directory in sorted(directories, key=lambda path: len(path.parts)):
            directory.mkdir(exist_ok=True)
            directory.chmod(0o755)
        for member in members:
            output = destination.joinpath(*PurePosixPath(member.name).parts)
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            if member.isdir():
                output.mkdir(exist_ok=True, mode=0o755)
            else:
                with source.extractfile(member) as incoming, output.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing, 65536)
                output.chmod(0o755 if member.mode & 0o111 else 0o644)


def release_version(path: Path) -> str:
    match = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"$', path.read_text(encoding="utf-8"), re.M)
    if not match:
        raise ValueError("Release version missing")
    return match.group(1)


def copy_upload(directory: Path, destination: Path, user: str, platform: str) -> str:
    trusted_path(destination)
    # Pin each directory component with O_NOFOLLOW before opening upload files.
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        if not directory.is_absolute() or ".." in directory.parts:
            raise ValueError("Upload directory must be absolute")
        for component in directory.parts[1:]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        def read_file(name, maximum):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
            with os.fdopen(fd, "rb") as incoming:
                info = os.fstat(incoming.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != pwd.getpwnam(user).pw_uid:
                    raise ValueError("Unexpected upload type or owner")
                data = incoming.read(maximum + 1)
                if len(data) > maximum:
                    raise ValueError("Upload exceeds size limit")
                return data
        metadata = json.loads(read_file("metadata.json", 4096))
        name = metadata["filename"]
        if not isinstance(name, str) or not re.fullmatch(r"bitcoin-\d+\.\d+(?:\.\d+)?-"+re.escape(platform)+r"\.tar\.gz", name):
            raise ValueError("Invalid upload filename")
        data = read_file("bitcoin-core-upload.tar.gz", 209715200)
        with (destination/name).open("xb") as output:
            output.write(data)
        return name
    finally:
        os.close(descriptor)


def rpc_health(credentials: Path, url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise ValueError("Health check RPC must be local")
    authorization = base64.b64encode(credentials.read_bytes().strip()).decode()
    request = urllib.request.Request(url,
        data=b'{"jsonrpc":"2.0","id":"health","method":"getblockchaininfo","params":[]}',
        headers={"Authorization":"Basic "+authorization,"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=5) as response:
        if json.load(response).get("error"):
            raise ValueError("Core RPC is not ready")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("paths", nargs="+", type=Path)
    version = commands.add_parser("version")
    version.add_argument("path", type=Path)
    extract = commands.add_parser("extract")
    extract.add_argument("archive", type=Path)
    extract.add_argument("destination", type=Path)
    extract.add_argument("prefix")
    extract.add_argument("maximum", type=int)
    upload = commands.add_parser("copy-upload")
    upload.add_argument("directory", type=Path)
    upload.add_argument("destination", type=Path)
    upload.add_argument("user")
    upload.add_argument("platform")
    health = commands.add_parser("rpc-health")
    health.add_argument("credentials", type=Path)
    health.add_argument("url")
    args = parser.parse_args()
    if args.command == "check":
        for path in args.paths:
            trusted_path(path)
    elif args.command == "version":
        trusted_path(args.path)
        print(release_version(args.path))
    elif args.command == "copy-upload":
        print(copy_upload(args.directory,args.destination,args.user,args.platform))
    elif args.command == "rpc-health":
        rpc_health(args.credentials,args.url)
    else:
        extract_archive(args.archive, args.destination, args.prefix, args.maximum)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        raise SystemExit(str(error))
