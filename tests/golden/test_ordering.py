"""The ordering golden test (Software Specification §9.2, guards OR-1..OR-3).

This is the single most important test in the system. It runs against every
synthetic manifest, whose prerequisites are ground truth, and asserts:

* OR-1 -- the acyclic portion of the agenda is a valid linear extension.
* The anti-priority-override META-TEST -- a higher-impact smell is NEVER
  placed before an unresolved prerequisite, even when impact would prefer
  it. Safety is never traded for priority.
* OR-3 -- cyclic smells are escalated, never silently ordered.
"""

from __future__ import annotations

import pytest

from seqrefactor.model import ImpactWeights
from seqrefactor.order.impact import score
from seqrefactor.order.orderer import order
from tests.support import expected_cycle_members, graph_from_manifest, list_subjects

DEFAULT_WEIGHTS = ImpactWeights()


@pytest.mark.parametrize("subject", list_subjects())
def test_ordering_is_safe_and_impact_forward(subject: str) -> None:
    from tests.support import load_manifest

    manifest = load_manifest(subject)
    g = graph_from_manifest(manifest)
    impact = score(g, DEFAULT_WEIGHTS)
    out = order(g, impact)

    pos = {s: i for i, s in enumerate(out.agenda)}

    # OR-1: every prerequisite precedes its dependent.
    for e in g.edges:
        if e.src in pos and e.dst in pos:
            assert pos[e.src] < pos[e.dst], (
                f"[{subject}] safety violated: {e.src} must precede {e.dst}"
            )

    # META-TEST: a higher-impact smell is NEVER placed before an unresolved
    # prerequisite, even when impact would prefer it. Safety still wins.
    for e in g.edges:
        if impact[e.dst] > impact[e.src] and e.src in pos and e.dst in pos:
            assert pos[e.src] < pos[e.dst], (
                f"[{subject}] impact override: {e.dst} outranks {e.src} but "
                "safety must still place the prerequisite first"
            )

    # OR-3: cyclic smells are escalated, never silently ordered.
    escalated = {s for comp in out.escalations for s in comp}
    assert escalated == expected_cycle_members(manifest), (
        f"[{subject}] escalation set mismatch: expected "
        f"{expected_cycle_members(manifest)}, got {escalated}"
    )
    assert escalated.isdisjoint(pos), f"[{subject}] an escalated smell leaked into the agenda"

    # Every node is accounted for exactly once: either ordered or escalated.
    assert set(pos) | escalated == g.node_ids()
    assert set(pos).isdisjoint(escalated)


def test_impact_forward_selection_among_ready_smells() -> None:
    """OR-2: among currently eligible smells, the orderer always selects the
    maximum-impact one (paper §Correctness, greedy choice for Eq. 2)."""
    manifest = load_manifest_pilot()
    g = graph_from_manifest(manifest)
    impact = score(g, DEFAULT_WEIGHTS)
    out = order(g, impact)

    # s1 (GodClass) is the sole root; all of s2..s7 become ready simultaneously
    # once s1 is emitted. Their relative order must be non-increasing impact.
    dependents = [sid for sid in out.agenda if sid != "s1"]
    dependent_impacts = [impact[sid] for sid in dependents]
    assert dependent_impacts == sorted(dependent_impacts, reverse=True)


def load_manifest_pilot():
    from tests.support import load_manifest

    return load_manifest("pilot_checkout_v1")
