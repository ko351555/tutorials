from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ystick.core.exceptions import FatalError

_JSON_BLOCK_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def parse_json_loose(raw: str) -> Any:
    """LLM output is sometimes wrapped in prose or markdown fences even
    when asked for pure JSON. Try strict parse first, then fall back to
    pulling out the first {...} or [...] block."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(raw)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise FatalError(f"could not parse JSON out of LLM output: {exc}\n---\n{raw[:2000]}") from exc
    raise FatalError(f"no JSON found in LLM output:\n---\n{raw[:2000]}")


def content_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]
