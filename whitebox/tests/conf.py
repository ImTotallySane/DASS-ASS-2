"""Pytest bootstrap for whitebox tests.

Ensures imports like `moneypoly.*` resolve by adding `whitebox/code`
to `sys.path` regardless of the current working directory.
"""

from pathlib import Path
import sys


def bootstrap_paths() -> None:
	"""Add the source root used by this project to sys.path."""
	whitebox_root = Path(__file__).resolve().parents[1]
	source_root = whitebox_root / "code"
	source_root_str = str(source_root)
	if source_root_str not in sys.path:
		sys.path.insert(0, source_root_str)


bootstrap_paths()

