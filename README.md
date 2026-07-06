# git-c2 — canary control center

A control center that lives on a git repo. HQ issues orders through one file,
the field reports findings into an append-only ledger, and a static page reads
the ledger back. The repo is the comms fabric — not the compute.

## Files

| File | Tier | Role |
|------|------|------|
| `orders.json` | HQ | Command surface: canaries, observer assignments, cadence. |
| `fo_core.py` | field | Pure detection + append-only ledger. Network-free. The trust boundary. |
| `fo_github.py` | observer | Polls GitHub code search for each canary, records hits. |
| `base_checkin.py` | base | Heartbeat writer for persistent hosts. |
| `.github/workflows/observer.yml` | HQ→field | Cron Action: self-test → sweep → commit ledger. |
| `ledger/hits.jsonl` | ledger | Append-only findings (written by observers). |
| `ledger/heartbeat.jsonl` | ledger | Append-only fleet status (written by bases). |

## Verify first (do this before anything else)

```bash
python fo_core.py --selftest
```

This plants `stoch-6x6` in a throwaway doc and asserts three things with no
network: the token is detected, it is *not* matched inside a larger token, and
a repeat (canary,url) is deduped. If that passes, the detector is sound and
every hit in the ledger is ground truth. Everything upstream is just a lead.

## Wire it up

1. Put a fine-grained PAT (public-repo read) in the repo secret `OBSERVER_PAT`.
2. Edit `orders.json` — your canaries and cadence.
3. Plant one canary somewhere public, then trigger the Action by hand
   (`workflow_dispatch`) and confirm it lands in `ledger/hits.jsonl`.
4. Point GitHub Pages at a small page that reads `hits.jsonl` and renders the map.

## What this catches — and what it does not

- It polls **indexes** (GitHub code search, and a web-search adapter you add as
  `fo-web`). It finds a canary only where a crawler already indexed it — so it
  tracks *published* propagation, not a token swallowed into a training set and
  never re-emitted.
- The GitHub match is fuzzy. Harden `fo_github.py` by fetching each candidate's
  raw blob and re-running `fo_core.scan_text` before recording (marked in-file).
- Actions is minute-limited on free tier and cron timing is best-effort, not
  exact. Fine for a daily/hourly sweep, not for real-time.
- git-as-C2 for a fleet of pollers is a legit GitOps pattern, but it also looks
  like beaconing malware to abuse detection. Stay in ToS and rate limits,
  respect each target's robots.txt, keep commit frequency sane.

## Command vs influence

Bases and observers are yours — full command. Public indexes are not — influence
only. The ledger records where your canary surfaced in that outside territory;
it does not give you any control over it.
