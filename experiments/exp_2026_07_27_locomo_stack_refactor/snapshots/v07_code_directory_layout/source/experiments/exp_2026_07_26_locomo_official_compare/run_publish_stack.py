#!/usr/bin/env python3
"""Compatibility entry point for the refactored LoCoMo/EM-graph stack."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from experiments.exp_2026_07_27_locomo_stack_refactor.run import main


if __name__ == "__main__":
    main()
