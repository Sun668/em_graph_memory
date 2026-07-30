"""Compatibility re-export for the shared model client.

New code imports :mod:`common.llm` directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "code"))

from common.llm import *  # noqa: F401,F403
from common.llm import _get_openai_client  # noqa: F401
