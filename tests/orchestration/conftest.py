"""Orchestration tests reuse the shared ``ctx`` fixture from tests/conftest.py.

This file just re-exports ``make_state`` for tests that build states directly.
"""

from __future__ import annotations

# Re-export so existing `from tests.orchestration.conftest import make_state`
# imports keep working; the ``ctx`` fixture is shared from tests/conftest.py.
from tests.conftest import make_state  # noqa: F401
