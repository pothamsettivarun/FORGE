from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


def session_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def append_jsonl(path: str, row: dict[str, Any]):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def write_json(path: str, data: dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
