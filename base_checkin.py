#!/usr/bin/env python3
"""Base check-in: write a heartbeat to the shared ledger.

Run on a persistent host from cron or a systemd timer. Records that this
base is alive and what it's doing, so HQ's map can show fleet status.

    NODE_ID=base-01 python base_checkin.py --status ok --note "idle"
"""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path

LEDGER_DIR = Path(os.environ.get("LEDGER_DIR", "ledger"))
BEAT = LEDGER_DIR / "heartbeat.jsonl"


def check_in(node_id: str, status: str, note: str) -> dict:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node": node_id,
        "kind": "base",
        "status": status,
        "note": note,
    }
    with BEAT.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--status", default="ok")
    p.add_argument("--note", default="")
    a = p.parse_args()
    node = os.environ.get("NODE_ID", "base-unknown")
    print(json.dumps(check_in(node, a.status, a.note)))
