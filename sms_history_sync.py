#!/usr/bin/env python3
"""
Read the phone's SMS inbox for the last 1 / 3 / 6 months and push it to smartMoney.

Runs on Android inside Termux (https://termux.dev) with the Termux:API app.

Setup (once, in Termux):
    pkg install python termux-api
    # install the "Termux:API" app too, then grant it SMS permission:
    termux-setup-storage            # optional
    # first call to termux-sms-list will prompt for the SMS permission

Usage:
    python sms_history_sync.py --months 3 \
        --endpoint https://your-server.com/api/sms/filter \
        --sender AlRajhiBank --sender STC \
        --header "Authorization: Bearer TOKEN"

    python sms_history_sync.py --months 1 --endpoint ... --dry-run   # preview only
"""
from __future__ import annotations

import argparse
import calendar
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Optional

VALID_MONTHS = (1, 3, 6, 12)


@dataclass(frozen=True)
class Sms:
    id: int
    sender: str
    body: str
    timestamp: datetime  # local time


# ---------------------------------------------------------------------------
# 1) READ
# ---------------------------------------------------------------------------

def months_ago(months: int, now: Optional[datetime] = None) -> datetime:
    """Calendar-aware 'N months back' (clamps day, e.g. Aug 31 - 6m -> Feb 28/29)."""
    now = now or datetime.now()
    total = now.year * 12 + (now.month - 1) - months
    year, month = divmod(total, 12)
    month += 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)


def _parse_received(value: str) -> datetime:
    value = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    if value.isdigit():  # epoch millis fallback
        return datetime.fromtimestamp(int(value) / 1000)
    raise ValueError(f"Unrecognised date format: {value!r}")


def _run_termux_sms_list(limit: int) -> list[dict]:
    try:
        proc = subprocess.run(
            ["termux-sms-list", "-t", "inbox", "-l", str(limit)],
            capture_output=True, text=True, timeout=120, check=True,
        )
    except FileNotFoundError:
        sys.exit("termux-sms-list not found. Run: pkg install termux-api "
                 "(and install the Termux:API app).")
    except subprocess.CalledProcessError as e:
        sys.exit(f"termux-sms-list failed: {e.stderr.strip() or e}")
    except subprocess.TimeoutExpired:
        sys.exit("termux-sms-list timed out (is SMS permission granted?).")
    return json.loads(proc.stdout or "[]")


def read_sms_history(
    months: int,
    allowed_senders: Optional[Iterable[str]] = None,
    *,
    fetch: Callable[[int], list[dict]] = _run_termux_sms_list,
    limit: int = 100_000,
    now: Optional[datetime] = None,
) -> list[Sms]:
    """Return received SMS from the last `months` months, oldest first."""
    if months not in VALID_MONTHS:
        raise ValueError(f"months must be one of {VALID_MONTHS}")

    cutoff = months_ago(months, now)
    senders = {s.lower() for s in allowed_senders} if allowed_senders else None

    result: list[Sms] = []
    for row in fetch(limit):
        sender, body = row.get("number"), row.get("body")
        if not sender or not body:
            continue
        if senders is not None and sender.lower() not in senders:
            continue
        try:
            ts = _parse_received(row["received"])
        except (KeyError, ValueError):
            continue
        if ts < cutoff:
            continue
        result.append(Sms(int(row.get("_id", 0)), sender, body, ts))

    result.sort(key=lambda s: s.timestamp)
    return result


# ---------------------------------------------------------------------------
# 2) PUSH
# ---------------------------------------------------------------------------

def default_payload(sms: Sms) -> dict:
    # ASSUMPTION: adjust to match what smartMoney's SMSController expects.
    return {
        "sender": sms.sender,
        "message": sms.body,
        "date": int(sms.timestamp.timestamp()),  # epoch seconds
    }


def _post(url: str, payload: dict, headers: dict[str, str], timeout: int) -> bool:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return 200 <= resp.status < 300


def push_sms_history(
    items: list[Sms],
    endpoint: str,
    *,
    headers: Optional[dict[str, str]] = None,
    build_payload: Callable[[Sms], dict] = default_payload,
    max_retries: int = 2,
    timeout: int = 15,
    delay_between: float = 0.2,
    on_progress: Callable[[int, int], None] = lambda done, total: None,
    post: Callable[..., bool] = _post,
) -> dict:
    """
    Send SMS one at a time (oldest first) with retry.
    Sequential on purpose: each accepted SMS triggers a parse job on the server,
    so this avoids flooding the queue / Firefly III / OpenAI.
    """
    headers = headers or {}
    sent = failed = 0

    for i, sms in enumerate(items, 1):
        ok = False
        for attempt in range(max_retries + 1):
            try:
                if post(endpoint, build_payload(sms), headers, timeout):
                    ok = True
                    break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            if attempt < max_retries:
                time.sleep(attempt + 1)
        sent += ok
        failed += not ok
        on_progress(i, len(items))
        time.sleep(delay_between)

    return {"total": len(items), "sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# 3) ONE-CALL CONVENIENCE + CLI
# ---------------------------------------------------------------------------

def sync_sms_history(months: int, endpoint: str, **kwargs) -> dict:
    senders = kwargs.pop("allowed_senders", None)
    items = read_sms_history(months, senders)
    return push_sms_history(items, endpoint, **kwargs)


def _parse_headers(values: list[str]) -> dict[str, str]:
    out = {}
    for h in values:
        name, sep, val = h.partition(":")
        if not sep:
            sys.exit(f"Bad --header {h!r}, expected 'Name: value'")
        out[name.strip()] = val.strip()
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Push SMS history to smartMoney")
    p.add_argument("--months", type=int, choices=VALID_MONTHS, required=True)
    p.add_argument("--endpoint", required=True, help="e.g. https://host/api/sms/filter")
    p.add_argument("--sender", action="append", default=[],
                   help="Only send SMS from this sender (repeatable)")
    p.add_argument("--header", action="append", default=[],
                   help="Extra header, e.g. 'Authorization: Bearer X' (repeatable)")
    p.add_argument("--dry-run", action="store_true", help="List what would be sent")
    args = p.parse_args()

    items = read_sms_history(args.months, args.sender or None)
    print(f"Found {len(items)} SMS in the last {args.months} month(s).")

    if args.dry_run:
        for s in items[:20]:
            print(f"  {s.timestamp:%Y-%m-%d %H:%M}  {s.sender}: {s.body[:60]!r}")
        if len(items) > 20:
            print(f"  ... and {len(items) - 20} more")
        return

    result = push_sms_history(
        items,
        args.endpoint,
        headers=_parse_headers(args.header),
        on_progress=lambda d, t: print(f"\r{d}/{t}", end="", flush=True),
    )
    print(f"\nDone: {result['sent']} sent, {result['failed']} failed of {result['total']}.")


if __name__ == "__main__":
    main()