#!/usr/bin/env python3
"""Real-time-ish SMS capture on Android via Termux.

Python counterpart of ``android/.../SmsReceiver.kt``. Android only delivers
``SMS_RECEIVED`` to native code, so a Python process cannot subscribe to the
broadcast; instead this script polls the inbox with ``termux-sms-list`` and
pushes new messages to the backend as soon as it sees them.

Setup (once, in Termux):

    pkg install python termux-api
    # install the "Termux:API" app and grant it SMS permission
    termux-wake-lock          # keeps Android from killing the script

Usage:

    python scripts/sms_receiver.py --base-url http://192.168.1.10:8000
    python scripts/sms_receiver.py --base-url http://192.168.1.10:8000 --once
    python scripts/sms_receiver.py --base-url ... --sender Bank --interval 10

The first run only remembers the current inbox (no history upload). Use
``--backfill`` to push everything that is already there.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

# Allow `python scripts/sms_receiver.py` and `python -m scripts.sms_receiver`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sms_sync import (
    DEFAULT_BASE_URL,
    DEFAULT_QUEUE,
    SyncResult,
    enqueue_and_sync,
    flush,
    normalize_base_url,
    pending_count,
    sms_item,
)

DEFAULT_STATE = Path.home() / ".sms_sync_seen.json"
SEEN_LIMIT = 5000


# ---------------------------------------------------------------------------
# Read the inbox
# ---------------------------------------------------------------------------

def read_inbox(limit: int) -> list[dict]:
    try:
        completed = subprocess.run(
            ["termux-sms-list", "-t", "inbox", "-l", str(limit)],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
    except FileNotFoundError:
        sys.exit(
            "termux-sms-list not found. Run: pkg install termux-api "
            "(and install the Termux:API app)."
        )
    except subprocess.CalledProcessError as error:
        sys.exit(f"termux-sms-list failed: {error.stderr.strip() or error}")
    except subprocess.TimeoutExpired:
        sys.exit("termux-sms-list timed out (is SMS permission granted?)")

    return json.loads(completed.stdout or "[]")


def parse_timestamp(row: dict) -> int:
    value = row.get("received", row.get("date"))

    if value is None:
        return int(time.time())

    if isinstance(value, (int, float)):
        number = int(value)
        return number // 1000 if number > 10_000_000_000 else number

    text = str(value).strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return int(datetime.strptime(text, pattern).timestamp())
        except ValueError:
            pass

    if text.isdigit():
        number = int(text)
        return number // 1000 if number > 10_000_000_000 else number

    return int(time.time())


def normalize(row: dict) -> dict | None:
    # Different Termux builds use "number"/"received" or "address"/"date".
    sender = row.get("number") or row.get("address")
    body = row.get("body")
    if not sender or not body:
        return None

    return {
        "id": int(row.get("_id", 0) or 0),
        "sender": str(sender),
        "message": str(body),
        "date": parse_timestamp(row),
    }


# ---------------------------------------------------------------------------
# Remember which messages were already handled
# ---------------------------------------------------------------------------

def load_seen(path: Path) -> list[int] | None:
    """Returns None when the state file does not exist (first run)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, list):
        return None

    return [int(value) for value in data if str(value).lstrip("-").isdigit()]


def save_seen(path: Path, ids: Iterable[int]) -> None:
    # Newest ids come first; keep a bounded history.
    values = list(dict.fromkeys(int(value) for value in ids))[:SEEN_LIMIT]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values), encoding="utf-8")


# ---------------------------------------------------------------------------
# One poll
# ---------------------------------------------------------------------------

def poll_once(
    base_url: str,
    queue_path: Path = DEFAULT_QUEUE,
    state_path: Path = DEFAULT_STATE,
    *,
    limit: int = 100,
    senders: Iterable[str] | None = None,
    backfill: bool = False,
    fetch: Callable[[int], list[dict]] = read_inbox,
    timeout: float = 20.0,
) -> SyncResult:
    seen = load_seen(state_path)
    first_run = seen is None
    seen = seen or []

    rows = [normalize(row) for row in fetch(limit)]
    rows = [row for row in rows if row is not None]

    allowed = {sender.lower() for sender in senders} if senders else None
    if allowed:
        rows = [row for row in rows if row["sender"].lower() in allowed]

    known = set(seen)
    fresh = [row for row in rows if row["id"] not in known]

    if first_run and not backfill:
        # Adopt the existing inbox instead of re-uploading its history.
        save_seen(state_path, [row["id"] for row in rows] + seen)
        return flush(base_url, queue_path, timeout=timeout)

    items = [sms_item(row["sender"], row["message"], row["date"]) for row in fresh]
    result = enqueue_and_sync(base_url, queue_path, items, timeout=timeout)

    save_seen(state_path, [row["id"] for row in rows] + seen)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SMS_BACKEND_URL", DEFAULT_BASE_URL),
        help="Backend root URL (default: %(default)s)",
    )
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--interval", type=float, default=20.0,
                        help="Seconds between inbox checks (default: 20)")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--sender", action="append", default=[],
                        help="Only watch this sender (repeatable)")
    parser.add_argument("--backfill", action="store_true",
                        help="Upload the existing inbox on the first run")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    def log(message: str) -> None:
        print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)

    interval = max(5.0, args.interval)
    log(f"Backend: {normalize_base_url(args.base_url)}")
    log(f"Queue:   {args.queue}")

    while True:
        try:
            result = poll_once(
                args.base_url,
                args.queue,
                args.state,
                limit=args.limit,
                senders=args.sender or None,
                backfill=args.backfill,
            )
        except KeyboardInterrupt:
            log("Stopped.")
            return
        except SystemExit:
            raise
        except Exception as error:  # keep the watcher alive
            log(f"Error: {error}")
        else:
            if result.error:
                log(
                    f"Backend unavailable ({result.error}); "
                    f"{result.pending} message(s) waiting in the queue"
                )
            elif result.queued or result.stored:
                log(
                    f"Synced {result.stored} new, "
                    f"{result.skipped} already on the server"
                )
            elif args.verbose:
                log(f"Nothing new ({pending_count(args.queue)} queued)")

        if args.once:
            return

        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            log("Stopped.")
            return


if __name__ == "__main__":
    main()
