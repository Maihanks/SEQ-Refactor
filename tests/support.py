"""Shared test helpers: load synthetic-subject manifests and derive ground truth from them.

Kept independent of seqrefactor.order.orderer and seqrefactor.graph.builder so that the
golden test (tests/golden/test_ordering.py) checks the orderer against ground truth that
was not itself produced by the code under test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import yaml

from seqrefactor.model import DepEdge, SmellDependencyGraph, SmellInstance

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets" / "synthetic"


def load_manifest(subject: str) -> dict[str, Any]:
    manifest_path = DATASETS_DIR / subject / "manifest.yaml"
    with manifest_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def list_subjects() -> list[str]:
    return sorted(p.name for p in DATASETS_DIR.iterdir() if (p / "manifest.yaml").is_file())


def graph_from_manifest(manifest: dict[str, Any]) -> SmellDependencyGraph:
    """Build a SmellDependencyGraph directly from a manifest's declared ground truth,
    independent of seqrefactor.graph.builder's derivation heuristics."""
    nodes = [
        SmellInstance(
            id=s["id"],
            category=s["category"],
            loc=list(s.get("loc", [])),
            severity=float(s.get("severity", 1.0)),
        )
        for s in manifest["smells"]
    ]
    edges = [
        DepEdge(src=p["src"], dst=p["dst"], provenance="manifest")
        for p in manifest.get("prerequisites", [])
    ]
    return SmellDependencyGraph(nodes=nodes, edges=edges)


def expected_cycle_members(manifest: dict[str, Any]) -> set[str]:
    """Ground-truth escalation set: every smell inside a non-trivial SCC of the
    manifest's declared prerequisite graph, computed independently via networkx."""
    g = nx.DiGraph()
    g.add_nodes_from(s["id"] for s in manifest["smells"])
    g.add_edges_from((p["src"], p["dst"]) for p in manifest.get("prerequisites", []))
    return {node for comp in nx.strongly_connected_components(g) if len(comp) > 1 for node in comp}
