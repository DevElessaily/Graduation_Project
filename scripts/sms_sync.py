#!/usr/bin/env python3
"""Backend sync + offline queue for SMS.

Python counterpart of ``android/.../SmsSync.kt``: it posts messages to
``POST /api/sms/bulk`` and keeps a JSON queue for anything that could not be
delivered (backend offline, wrong URL, no Wi-Fi).

Runs on the phone in Termux, but works on any machine:

    python scripts/sms_sync.py --base-url http://192.168.1.10:8000 \
        --add "Bank" "You paid 50 EGP"

    python scripts/sms_sync.py --base-url http://192.168.1.10:8000 --flush
    python scripts/sms_sync.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_BASE_URL = os.environ.get("SMS_BACKEND_URL", "http://127.0.0.1:8000")
DEFAULT_QUEUE = Path.home() / ".sms_sync_queue.json"
CHUNK_SIZE = 100


@dataclass
class SyncResult:
    stored: int = 0
    skipped: int = 0
    failed: int = 0
    pending: int = 0
    queued: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_dict(self) -> dict:
        return {
            "stored": self.stored,
            "skipped": self.skipped,
            "failed": self.failed,
            "pending": self.pending,
            "queued": self.queued,
            "error": self.error,
        }


def normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def sms_item(sender: str, message: str, date: int | None = None) -> dict:
    """One entry of the ``/api/sms/bulk`` payload (date is epoch seconds)."""
    return {
        "sender": sender,
        "message": message,
        "date": int(time.time()) if date is None else int(date),
    }


def _key(item: dict) -> tuple[str, str, int]:
    return (
        str(item.get("sender", "")),
        str(item.get("message", "")),
        int(item.get("date", 0) or 0),
    )


# ---------------------------------------------------------------------------
# Offline queue
# ---------------------------------------------------------------------------

def load_queue(path: Path) -> list[dict]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def save_queue(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not items:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def enqueue(path: Path, items: Iterable[dict]) -> int:
    """Adds messages to the queue, ignoring duplicates. Returns how many were added."""
    queue = load_queue(path)
    known = {_key(item) for item in queue}

    added = 0
    for item in items:
        key = _key(item)
        if key in known:
            continue
        known.add(key)
        queue.append(item)
        added += 1

    if added:
        save_queue(path, queue)

    return added


def pending_count(path: Path) -> int:
    return len(load_queue(path))


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def post_bulk(
    base_url: str,
    items: Iterable[dict],
    timeout: float = 20.0,
) -> dict:
    url = f"{normalize_base_url(base_url)}/api/sms/bulk"
    payload = json.dumps(
        {"items": list(items)},
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:160]
        raise RuntimeError(f"HTTP {error.code} {detail}".strip()) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Cannot reach {url}: {error.reason}") from error
    except OSError as error:
        raise RuntimeError(f"Cannot reach {url}: {error}") from error

    return json.loads(body) if body else {}


def flush(
    base_url: str,
    queue_path: Path = DEFAULT_QUEUE,
    timeout: float = 20.0,
) -> SyncResult:
    """Sends queued messages in chunks, dropping each chunk only once accepted."""
    queue = load_queue(queue_path)
    if not queue:
        return SyncResult()

    stored = 0
    skipped = 0

    while queue:
        batch = queue[:CHUNK_SIZE]
        try:
            response = post_bulk(base_url, batch, timeout=timeout)
        except RuntimeError as error:
            # Keep everything, including the batch we just tried.
            save_queue(queue_path, queue)
            return SyncResult(
                stored=stored,
                skipped=skipped,
                failed=len(batch),
                pending=len(queue),
                error=str(error),
            )

        stored += int(response.get("stored", 0))
        skipped += int(response.get("skipped", 0))
        queue = queue[CHUNK_SIZE:]
        save_queue(queue_path, queue)

    return SyncResult(stored=stored, skipped=skipped, pending=0)


def enqueue_and_sync(
    base_url: str,
    queue_path: Path,
    items: Iterable[dict],
    timeout: float = 20.0,
) -> SyncResult:
    added = enqueue(queue_path, items)
    result = flush(base_url, queue_path, timeout=timeout)
    result.queued = added
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--add",
        nargs="+",
        metavar=("SENDER", "MESSAGE"),
        help="Queue one SMS and try to send it",
    )
    parser.add_argument("--date", type=int, help="Epoch seconds for --add (default: now)")
    parser.add_argument("--flush", action="store_true", help="Send the queue")
    parser.add_argument("--status", action="store_true", help="Show the queue size")
    args = parser.parse_args()

    if args.add:
        sender, message = args.add[0], " ".join(args.add[1:])
        result = enqueue_and_sync(
            args.base_url,
            args.queue,
            [sms_item(sender, message, args.date)],
            timeout=args.timeout,
        )
        print(json.dumps(result.as_dict(), indent=2))
        return

    if args.flush:
        result = flush(args.base_url, args.queue, timeout=args.timeout)
        print(json.dumps(result.as_dict(), indent=2))
        return

    if args.status:
        print(json.dumps({"pending": pending_count(args.queue), "queue": str(args.queue)}, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
