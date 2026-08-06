"""`ystick-ui` console entrypoint — thin wrapper so users don't need to
remember the streamlit invocation path."""
from __future__ import annotations

import sys
from pathlib import Path

APP_PATH = Path(__file__).parent / "app.py"


def main() -> None:
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print("Streamlit isn't installed. Run: pip install -e '.[ui]'", file=sys.stderr)
        raise SystemExit(1)

    sys.argv = ["streamlit", "run", str(APP_PATH), *sys.argv[1:]]
    raise SystemExit(stcli.main())
