#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "Run with sudo: sudo bash $0" >&2; exit 1; }
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v snmpget >/dev/null || { echo "Install the Net-SNMP client package first" >&2; exit 1; }
getent group nocmon >/dev/null || groupadd --system nocmon
id nocmon >/dev/null 2>&1 || useradd --system --gid nocmon --home-dir /var/lib/nocmon --shell /usr/sbin/nologin nocmon
install -d -m 0755 /opt/nocmon/src/nocmon /etc/nocmon
cp -a "$HERE/src/nocmon/." /opt/nocmon/src/nocmon/
if [[ ! -f /etc/nocmon/devices.json ]]; then install -o root -g nocmon -m 0640 "$HERE/config/devices.json" /etc/nocmon/devices.json; fi
install -m 0644 "$HERE/systemd/nocmon.service" "$HERE/systemd/nocmon.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now nocmon.timer
echo "Installed. Check systemctl status nocmon.timer and journalctl -u nocmon.service"
