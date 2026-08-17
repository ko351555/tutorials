from __future__ import annotations

import re
from datetime import date


def slugify(text: str, max_words: int = 8) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    words = text.split()[:max_words]
    return "-".join(words) or "untitled"


def new_project_id(seed: str) -> str:
    return f"{slugify(seed)}-{date.today().isoformat()}"
