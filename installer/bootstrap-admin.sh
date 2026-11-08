#!/bin/sh
# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
test "$(id -u)" -eq 0 || { echo "Run as root" >&2; exit 1; }
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec /usr/bin/python3 -I "$script_dir/harden_installation.py"
