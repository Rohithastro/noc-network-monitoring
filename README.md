# Project 2 — NOC Network Monitoring System

An SNMP-based NOC monitor that polls configured network devices, records availability and latency in SQLite, detects up/down transitions, emits alerts, and creates uptime/downtime reports.

## Requirements

Linux, Python 3.9+, and Net-SNMP client tools (`snmpget`). On Debian/Ubuntu: `sudo apt install snmp snmpd`. On a disposable VM, copy `snmpd-demo.conf` to `/etc/snmp/snmpd.conf` and restart `snmpd`; it binds only to loopback. Then run the included localhost target.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
PYTHONPATH=src python3 -m nocmon --config config/devices.json poll
PYTHONPATH=src python3 -m nocmon --config config/devices.json report --hours 24
```

Copy config and set target addresses/community for devices in your lab. The included target is localhost and the demo agent is loopback-only. This prototype supports SNMPv2c only; its community string is not encrypted. Do not expose it to untrusted networks. For production, extend the poller for SNMPv3 authPriv and use a dedicated management network.

Poll once per minute with `sudo bash scripts/install.sh`; inspect `systemctl status nocmon.timer`, `journalctl -u nocmon.service`, and `/var/lib/nocmon/monitor.db`. Reports can be written as Markdown or CSV. Availability and downtime are estimates based on polling samples; treat periods with sparse samples as incomplete coverage.

## What to present

Show sysUpTime polling, the SQLite sample history, an up/down transition alert, and the 24-hour report. Explain polling interval, timeouts, SNMP community limitations, and how sample-based availability is estimated. `alert_webhook` is optional and should point only to an endpoint you control.

