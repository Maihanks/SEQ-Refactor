"""Synthetic-subject manifest loading (Software Specification §8.1; Working
Brief §7). The golden ordering test (tests/golden/test_ordering.py) and the
dependency-mass study (seqrefactor/eval/depmass.py, via eval/tables.py) both
need the same declared ground-truth structure -- this is the one place it is
read from YAML, so neither can drift from the other.
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
    independent of seqrefactor.graph.builder's derivation heuristics.

    ``positive_dependencies`` and ``negative_dependencies`` (Working Brief §7:
    "for synthetic subjects, the injected positive/negative dependencies so the
    dependency-mass study has ground truth") are hand-declared the same way
    ``prerequisites`` already is -- injected ground truth for evaluation, not
    required to match what graph_builder.build's catalogue/containment
    heuristics would independently derive from these smells.
    """
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
    edges += [
        DepEdge(
            src=p["src"],
            dst=p["dst"],
            provenance="manifest:positive",
            polarity="positive",
            probability=float(p.get("probability", 1.0)),
            inducing_operation=p.get("operation"),
        )
        for p in manifest.get("positive_dependencies", [])
    ]
    edges += [
        DepEdge(
            src=p["src"],
            dst=p["dst"],
            provenance="manifest:negative",
            polarity="negative",
            probability=float(p.get("probability", 1.0)),
            inducing_operation=p.get("operation"),
        )
        for p in manifest.get("negative_dependencies", [])
    ]
    return SmellDependencyGraph(nodes=nodes, edges=edges)


def expected_cycle_members(manifest: dict[str, Any]) -> set[str]:
    """Ground-truth escalation set: every smell inside a non-trivial SCC of the
    manifest's declared prerequisite graph, computed independently via networkx."""
    g = nx.DiGraph()
    g.add_nodes_from(s["id"] for s in manifest["smells"])
    g.add_edges_from((p["src"], p["dst"]) for p in manifest.get("prerequisites", []))
    return {node for comp in nx.strongly_connected_components(g) if len(comp) > 1 for node in comp}
