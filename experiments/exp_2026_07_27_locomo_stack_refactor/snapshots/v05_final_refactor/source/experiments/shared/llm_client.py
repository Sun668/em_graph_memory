"""Compatibility re-export for the shared model client.

New code imports :mod:`common.llm` directly.
"""

from common.llm import *  # noqa: F401,F403
from common.llm import _get_openai_client  # noqa: F401

