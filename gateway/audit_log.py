import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "audit.log"
_GENESIS_HASH = "0" * 64
_lock = threading.Lock()


def _read_last_hash() -> str:
    if not _LOG_PATH.exists():
        return _GENESIS_HASH

    last_line = None
    with _LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line

    if last_line is None:
        return _GENESIS_HASH
    return json.loads(last_line)["hash"]


_last_hash = _read_last_hash()


def _compute_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_event(
    event_type: str,
    client_id: str | None,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> None:
    # detail must never contain raw message content, credentials, or other
    # sensitive values — only counts, categories, and booleans. The audit
    # log is itself a trusted sink (THREAT_MODEL.md), not a place to stash
    # the exact data the rest of the gateway exists to protect.
    global _last_hash

    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "client_id": client_id,
        "outcome": outcome,
        "detail": detail or {},
    }

    with _lock:
        record["prev_hash"] = _last_hash
        record["hash"] = _compute_hash(record)

        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

        _last_hash = record["hash"]


def verify_log() -> tuple[bool, str]:
    if not _LOG_PATH.exists():
        return True, "no audit log found; nothing to verify"

    expected_prev = _GENESIS_HASH
    count = 0

    with _LOG_PATH.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            record = json.loads(line)
            stored_hash = record.pop("hash")

            if record.get("prev_hash") != expected_prev:
                return False, f"chain broken at line {line_number}: unexpected prev_hash"
            if _compute_hash(record) != stored_hash:
                return False, f"chain broken at line {line_number}: hash mismatch (entry tampered)"

            expected_prev = stored_hash
            count += 1

    return True, f"audit log verified: {count} entries, chain intact"
