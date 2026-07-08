"""Test configuration.

Skip real PDF compilation during tests — it is slow and not what the tests
assert (LaTeX *validity* is covered by compiling once in CI / manually). The
whole pipeline, gates, compounding, and paper generation still run.
"""
from __future__ import annotations

import os

os.environ.setdefault("DARKFACTORY_SKIP_PDF", "1")
