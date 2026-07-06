#!/usr/bin/env python3
"""Forward-observer core: pure detection + append-only ledger.

Detection is deliberately separated from all network I/O so it can be
verified against a planted string with zero external dependencies.
Run the self-test first, always:

    python fo_core.py --selftest
"""
from __future__ import annotations
import json, os, sys, time, hashlib, re
from pathlib import Path

LEDGER_DIR = Path(os.environ.get("LEDGER_DIR", "ledger"))
HITS = LEDGER_DIR / "hits.jsonl"
SEEN = LEDGER_DIR / ".seen"        # dedupe index: one fingerprint per line


def scan_text(text: str, canaries: list[str]) -> list[str]:
    """Return the canaries that literally appear in text.

    Case-sensitive, and the token must stand alone -- not embedded inside
    a larger identifier. This is the whole trust boundary: a hit here is
    ground truth, everything upstream (search APIs) is merely a lead.
    """
    found = []
    for c in canaries:
        pat = r"(?<![A-Za-z0-9_-])" + re.escape(c) + r"(?![A-Za-z0-9_-])"
        if re.search(pat, text):
            found.append(c)
    return found


def _fingerprint(canary: str, url: str) -> str:
    return hashlib.sha256(f"{canary}\x00{url}".encode()).hexdigest()[:16]


def _load_seen() -> set[str]:
    return set(SEEN.read_text().split()) if SEEN.exists() else set()


def record_hit(canary: str, url: str, source: str, observer: str,
               snippet: str = "", ts: str | None = None) -> bool:
    """Append a hit unless (canary,url) was already recorded.

    Returns True if newly written, False if it was a duplicate.
    """
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    fp = _fingerprint(canary, url)
    if fp in _load_seen():
        return False
    entry = {
        "ts": ts or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "observer": observer,
        "canary": canary,
        "source": source,
        "url": url,
        "snippet": snippet[:280],
        "fp": fp,
    }
    with HITS.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    with SEEN.open("a") as f:
        f.write(fp + "\n")
    return True


def load_orders(path: str = "orders.json") -> dict:
    return json.loads(Path(path).read_text())


def _selftest() -> int:
    """Plant a string, prove detection + boundary + dedupe. No network."""
    import tempfile, shutil
    global LEDGER_DIR, HITS, SEEN
    tmp = Path(tempfile.mkdtemp())
    LEDGER_DIR, HITS, SEEN = tmp, tmp / "hits.jsonl", tmp / ".seen"
    try:
        canaries = ["stoch-6x6", "STOICHEION-7Q9"]
        doc = "readme\n... see build stoch-6x6 in the appendix ...\n"
        assert scan_text(doc, canaries) == ["stoch-6x6"], "detection failed"
        assert scan_text("prestoch-6x6x", canaries) == [], "boundary failed"
        a = record_hit("stoch-6x6", "https://example.com/a", "test", "fo-selftest")
        b = record_hit("stoch-6x6", "https://example.com/a", "test", "fo-selftest")
        assert a is True and b is False, "dedupe failed"
        assert len(HITS.read_text().splitlines()) == 1, "ledger line count wrong"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest ok: detection + boundary + dedupe all pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest() if "--selftest" in sys.argv
                     else (print("usage: fo_core.py --selftest") or 1))
