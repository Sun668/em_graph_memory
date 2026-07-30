"""Compatibility re-export for :mod:`common.codex`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "code"))

from common.codex import *  # noqa: F401,F403
