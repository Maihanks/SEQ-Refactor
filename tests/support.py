"""Shared test helpers: load synthetic-subject manifests and derive ground truth
from them.

Re-exports seqrefactor.datasets, which is where the loading logic actually
lives (it's also needed by production eval code, e.g. eval/tables.py's
Table III -- see that module's docstring), so this stays the single test-side
entry point without duplicating the implementation.

Kept independent of seqrefactor.order.orderer and seqrefactor.graph.builder so
that the golden test (tests/golden/test_ordering.py) checks the orderer
against ground truth that was not itself produced by the code under test.
"""

from __future__ import annotations

from seqrefactor.datasets import (
    DATASETS_DIR,
    expected_cycle_members,
    graph_from_manifest,
    list_subjects,
    load_manifest,
)

__all__ = [
    "DATASETS_DIR",
    "expected_cycle_members",
    "graph_from_manifest",
    "list_subjects",
    "load_manifest",
]
