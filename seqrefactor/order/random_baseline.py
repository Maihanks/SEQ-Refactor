"""Random and random-topological ordering baselines (Working Brief Phase 2c §3).

Two reference strategies that separate what safety and impact-forward
priority each contribute on their own, which the existing five-strategy
suite could not:

- ``random``: an unconstrained random permutation, ignoring every
  prerequisite edge entirely. Measures how often an arbitrary order is
  unsafe, giving the cascading-violation rate a meaningful upper reference.
- ``random_topological``: safe by construction (every prerequisite is
  honoured) but impact-neutral. Comparing SEQ-REFACTOR against this isolates
  the value of impact-forward prioritisation from the value of safety alone
  (``random`` isolates the reverse: how much unsafety exists to be fixed).

Neither function modifies ``order/orderer.py`` (out of scope, per the
brief): ``random_topological_order`` is obtained by feeding independently
drawn random priorities into the existing, UNCHANGED priority-queue-Kahn
decoder, the same reuse pattern ``order/search_based.py`` already uses for
its genetic search. Every output is still a genuinely safe linear
extension, produced by code that was never touched for this purpose.

HONESTY NOTE: this is not an exactly uniform sample over all linear
extensions of the prerequisite graph. Exact uniform sampling over the linear
extensions of a general poset is #P-hard (Brightwell and Winkler, 1991), so
no practical implementation reaches it exactly. Random-priority Kahn
traversal is the standard, honest practical approximation: independently
drawn each call, always valid and safe, not provably uniform.
"""

from __future__ import annotations

import random

from seqrefactor.model import Ordering, SmellDependencyGraph
from seqrefactor.order.orderer import order as decode_order


def random_order(graph: SmellDependencyGraph, seed: int) -> Ordering:
    """An unconstrained random permutation of every vertex, ignoring
    prerequisites entirely -- unsafe by construction whenever the graph has
    any real prerequisite edge and the random draw happens to violate it."""
    rng = random.Random(seed)
    agenda = [n.id for n in graph.nodes]
    rng.shuffle(agenda)
    return Ordering(agenda=agenda, escalations=[])


def random_topological_order(graph: SmellDependencyGraph, seed: int) -> Ordering:
    """A safe (dependency-respecting), impact-neutral linear extension: the
    unmodified decoder (``orderer.order``) run with i.i.d. random priorities
    instead of real impact scores. See module HONESTY NOTE for what
    "random" does and does not guarantee about the resulting distribution.
    """
    rng = random.Random(seed)
    random_priorities = {n.id: rng.random() for n in graph.nodes}
    return decode_order(graph, random_priorities)
