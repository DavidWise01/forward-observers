#!/usr/bin/env python3
"""Forward observer: GitHub code-search adapter.

Polls the GitHub code-search API for each canary in orders.json and records
hits to the ledger via fo_core. Requires GH_TOKEN (a fine-grained PAT with
public-repo read is enough):

    GH_TOKEN=ghp_xxx python fo_github.py

HONESTY NOTE: GitHub's code search is an *index lookup*, not ground truth --
it returns items where the token was indexed, and matching is fuzzy. The
strict version fetches each candidate's raw content and re-runs
fo_core.scan_text on it before recording. This skeleton records on the
server match plus the repo/path context; wire in the raw re-verify (marked
below) before you trust the ledger for anything load-bearing.
"""
from __future__ import annotations
import os, sys, time
import urllib.request, urllib.parse, json
import fo_core

API = "https://api.github.com/search/code"
OBSERVER = "fo-github"


def search(canary: str, token: str) -> list[dict]:
    q = urllib.parse.urlencode({"q": f'"{canary}"', "per_page": 30})
    req = urllib.request.Request(
        f"{API}?{q}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "forward-observer",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("items", [])
    except urllib.error.HTTPError as e:
        if e.code in (403, 422):
            print(f"github: {e.code} (rate-limit/validation); backing off",
                  file=sys.stderr)
            return []
        raise


def run() -> int:
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("GH_TOKEN not set", file=sys.stderr)
        return 2
    canaries = fo_core.load_orders().get("canaries", [])
    new = 0
    for canary in canaries:
        for item in search(canary, token):
            url = item.get("html_url", "")
            repo = item.get("repository", {}).get("full_name", "")
            context = f"{repo} {item.get('path', '')}"
            # --- strict re-verify goes HERE: fetch raw blob, then ---
            # if not fo_core.scan_text(raw, [canary]): continue
            if fo_core.record_hit(canary, url, "github_code", OBSERVER, context):
                new += 1
            time.sleep(2)  # be polite to the API
    print(f"{OBSERVER}: {new} new hit(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
