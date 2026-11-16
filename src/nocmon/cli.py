"""SNMP polling, alert transition tracking, and availability reports."""
import argparse
import csv
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SYS_UPTIME = "1.3.6.1.2.1.1.3.0"


def init_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS samples (id INTEGER PRIMARY KEY, name TEXT, host TEXT, checked_at TEXT, up INTEGER, latency_ms REAL, uptime_ticks INTEGER, error TEXT)")
        db.execute("CREATE INDEX IF NOT EXISTS sample_time ON samples(checked_at)")
        db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, name TEXT, host TEXT, occurred_at TEXT, event TEXT, detail TEXT)")


def poll_device(device, timeout):
    start = time.monotonic()
    if not shutil.which("snmpget"):
        return {"up": False, "latency_ms": None, "uptime_ticks": None, "error": "snmpget command not found; install Net-SNMP clients"}
    args = ["snmpget", "-v2c", "-c", device["community"], "-Oqv", "-t", str(timeout), "-r", "0",
            "{}:{}".format(device["host"], int(device.get("port", 161))), SYS_UPTIME]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 2, check=False)
        elapsed = round((time.monotonic() - start) * 1000, 2)
        if proc.returncode:
            return {"up": False, "latency_ms": elapsed, "uptime_ticks": None,
                    "error": (proc.stderr.strip() or proc.stdout.strip() or "SNMP query failed")[:300]}
        match = re.search(r"\((\d+)\)", proc.stdout)
        return {"up": True, "latency_ms": elapsed, "uptime_ticks": int(match.group(1)) if match else None, "error": None}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"up": False, "latency_ms": round((time.monotonic() - start) * 1000, 2), "uptime_ticks": None, "error": str(exc)[:300]}


def alert(config, event):
    print(json.dumps({"alert": event}, sort_keys=True))
    url = config.get("alert_webhook")
    if url:
        body = json.dumps(event).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=3):
                pass
        except OSError as exc:
            print("webhook delivery failed: {}".format(exc), file=sys.stderr)


def do_poll(config):
    path = config["database"]
    init_db(path)
    checked_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as db:
        for device in config["devices"]:
            result = poll_device(device, float(config.get("timeout_seconds", 2)))
            row = db.execute("SELECT up FROM samples WHERE name=? ORDER BY id DESC LIMIT 1", (device["name"],)).fetchone()
            db.execute("INSERT INTO samples(name,host,checked_at,up,latency_ms,uptime_ticks,error) VALUES(?,?,?,?,?,?,?)",
                       (device["name"], device["host"], checked_at, int(result["up"]), result["latency_ms"], result["uptime_ticks"], result["error"]))
            state = int(result["up"])
            if row is None and not state:
                alert(config, {"device": device["name"], "host": device["host"], "event": "DOWN", "time": checked_at, "detail": result["error"]})
                db.execute("INSERT INTO events(name,host,occurred_at,event,detail) VALUES(?,?,?,?,?)", (device["name"], device["host"], checked_at, "DOWN", result["error"]))
            elif row is not None and row[0] != state:
                label = "UP" if state else "DOWN"
                alert(config, {"device": device["name"], "host": device["host"], "event": label, "time": checked_at, "detail": result["error"]})
                db.execute("INSERT INTO events(name,host,occurred_at,event,detail) VALUES(?,?,?,?,?)", (device["name"], device["host"], checked_at, label, result["error"]))
            print("{:<20} {} {} ms {}".format(device["name"], "UP" if state else "DOWN", result["latency_ms"], result["error"] or ""))


def make_report(config, hours):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with sqlite3.connect(config["database"]) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT name,host,COUNT(*) samples,SUM(up) up_samples,AVG(latency_ms) avg_latency,MIN(checked_at) first_seen,MAX(checked_at) last_seen FROM samples WHERE checked_at>=? GROUP BY name,host ORDER BY name", (cutoff,)).fetchall()
        events = db.execute("SELECT name,host,occurred_at,event,detail FROM events WHERE occurred_at>=? ORDER BY occurred_at DESC", (cutoff,)).fetchall()
    devices = []
    for row in rows:
        ratio = row["up_samples"] / row["samples"] if row["samples"] else 0
        devices.append({"name": row["name"], "host": row["host"], "samples": row["samples"],
                        "availability_percent": round(ratio * 100, 3), "estimated_downtime_minutes": round((1-ratio) * hours * 60, 2),
                        "average_latency_ms": round(row["avg_latency"], 2) if row["avg_latency"] is not None else None,
                        "first_seen": row["first_seen"], "last_seen": row["last_seen"]})
    return {"period_hours": hours, "generated_at": datetime.now(timezone.utc).isoformat(), "devices": devices,
            "events": [dict(event) for event in events]}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nocmon", description="SNMP NOC monitor and reporter")
    parser.add_argument("--config", required=True)
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("poll")
    report = subs.add_parser("report")
    report.add_argument("--hours", type=float, default=24)
    report.add_argument("--format", choices=("text", "json", "csv"), default="text")
    report.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if args.action == "poll":
            do_poll(config)
            return 0
        if args.hours <= 0:
            raise ValueError("hours must be positive")
        data = make_report(config, args.hours)
        if args.format == "json":
            rendered = json.dumps(data, indent=2)
        elif args.format == "csv":
            from io import StringIO
            buffer = StringIO()
            writer = csv.DictWriter(buffer, fieldnames=data["devices"][0].keys() if data["devices"] else ["name", "host", "samples", "availability_percent", "estimated_downtime_minutes", "average_latency_ms", "first_seen", "last_seen"])
            writer.writeheader(); writer.writerows(data["devices"])
            rendered = buffer.getvalue()
        else:
            lines = ["NOC Availability Report — last {} hours".format(args.hours), ""]
            lines.extend("- **{name}** ({host}): {availability_percent}% availability; estimated downtime {estimated_downtime_minutes} min; avg latency {average_latency_ms} ms; {samples} samples".format(**item) for item in data["devices"])
            lines += ["", "Recent state-change events:"]
            lines.extend("- {} {} {} — {}".format(event["occurred_at"], event["name"], event["event"], event["detail"] or "") for event in data["events"])
            rendered = "\n".join(lines) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="" if rendered.endswith("\n") else "\n")
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, json.JSONDecodeError) as exc:
        print("nocmon: {}".format(exc), file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
