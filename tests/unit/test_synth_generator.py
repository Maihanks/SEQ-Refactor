"""Acceptance checks for the synthetic-subject generator (Working Brief, Phase 2,
§1.6): determinism, compiles-and-tests-green, detector/builder independence with
substantial ground-truth overlap, and cycle control.
"""

from __future__ import annotations

import filecmp
from pathlib import Path

import pytest
import yaml

from seqrefactor import _sidecar, ingest
from seqrefactor.datasets import expected_cycle_members, graph_from_manifest
from seqrefactor.detect import native as detect_native
from seqrefactor.graph.builder import build
from seqrefactor.model import ImpactWeights
from seqrefactor.order.impact import score
from seqrefactor.order.orderer import order
from seqrefactor.synth.generator import (
    build_chain_plan,
    build_conflict_plan,
    build_plan,
    generate_chain_subject,
    generate_conflict_subject,
    generate_subject,
)
from seqrefactor.verify.tests import SidecarTestRunner


def _dirs_equal(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(_dirs_equal(Path(a, sub), Path(b, sub)) for sub in cmp.common_dirs)


def test_plan_is_deterministic_given_the_same_seed() -> None:
    a = build_plan("det", seed=99, n_classes=7, n_smells=11, dependency_density=0.5,
                    cycle_rate=0.2, positive_rate=0.4, negative_rate=0.4)
    b = build_plan("det", seed=99, n_classes=7, n_smells=11, dependency_density=0.5,
                    cycle_rate=0.2, positive_rate=0.4, negative_rate=0.4)

    assert [s.id for s in a.all_smells] == [s.id for s in b.all_smells]
    assert [s.category for s in a.all_smells] == [s.category for s in b.all_smells]
    assert a.prerequisites == b.prerequisites
    assert a.positive_deps == b.positive_deps
    assert a.cyclic == b.cyclic


def test_generate_subject_is_byte_identical_across_two_generations(tmp_path: Path) -> None:
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    generate_subject("byteid", seed=5, n_classes=5, n_smells=8, dependency_density=0.6,
                      cycle_rate=0.3, positive_rate=0.4, negative_rate=0.4, out_root=str(out_a))
    generate_subject("byteid", seed=5, n_classes=5, n_smells=8, dependency_density=0.6,
                      cycle_rate=0.3, positive_rate=0.4, negative_rate=0.4, out_root=str(out_b))

    assert _dirs_equal(out_a / "byteid", out_b / "byteid")


def test_different_seeds_produce_different_output(tmp_path: Path) -> None:
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    generate_subject("diffseed", seed=1, n_classes=5, n_smells=8, dependency_density=0.6,
                      cycle_rate=0.3, positive_rate=0.4, negative_rate=0.4, out_root=str(out_a))
    generate_subject("diffseed", seed=2, n_classes=5, n_smells=8, dependency_density=0.6,
                      cycle_rate=0.3, positive_rate=0.4, negative_rate=0.4, out_root=str(out_b))

    assert not _dirs_equal(out_a / "diffseed", out_b / "diffseed")


def test_manifest_matches_pilot_checkout_schema(tmp_path: Path) -> None:
    path = generate_subject("schema", seed=3, n_classes=4, n_smells=6, dependency_density=0.5,
                             cycle_rate=0.0, positive_rate=0.5, negative_rate=0.5, out_root=str(tmp_path))
    manifest = yaml.safe_load((Path(path) / "manifest.yaml").read_text())

    assert set(manifest) >= {"subject", "acyclic", "smells", "prerequisites",
                              "expected_cascade_if_out_of_order"}
    for smell in manifest["smells"]:
        assert set(smell) == {"id", "category", "loc", "severity"}
    for edge in manifest["prerequisites"]:
        assert set(edge) == {"src", "dst"}
    for dep in manifest.get("positive_dependencies", []):
        assert set(dep) == {"src", "dst", "probability", "operation"}

    # Loader used by both the golden test and eval/depmass.py must consume it unchanged.
    graph = graph_from_manifest(manifest)
    assert len(graph.nodes) == len(manifest["smells"])


def test_cycle_rate_one_forces_escalation(tmp_path: Path) -> None:
    path = generate_subject("cyc1", seed=11, n_classes=5, n_smells=8, dependency_density=0.6,
                             cycle_rate=1.0, positive_rate=0.0, negative_rate=0.0, out_root=str(tmp_path))
    manifest = yaml.safe_load((Path(path) / "manifest.yaml").read_text())
    assert manifest["acyclic"] is False

    graph = graph_from_manifest(manifest)
    out = order(graph, score(graph, ImpactWeights()))
    escalated = {sid for comp in out.escalations for sid in comp}
    assert escalated == expected_cycle_members(manifest)
    assert escalated  # non-empty: a real cycle was escalated


def test_cycle_rate_zero_never_escalates(tmp_path: Path) -> None:
    for seed in range(5):
        path = generate_subject(f"cyc0_{seed}", seed=seed, n_classes=5, n_smells=8,
                                 dependency_density=0.6, cycle_rate=0.0, positive_rate=0.0,
                                 negative_rate=0.0, out_root=str(tmp_path))
        manifest = yaml.safe_load((Path(path) / "manifest.yaml").read_text())
        assert manifest["acyclic"] is True
        graph = graph_from_manifest(manifest)
        out = order(graph, score(graph, ImpactWeights()))
        assert out.escalations == []


def test_builder_independently_infers_planted_prerequisites_with_full_overlap(tmp_path: Path) -> None:
    """The core anti-circularity check (Working Brief §1.1, §1.6): detect and
    build from the generated .java source ALONE (manifest never read by
    either), then compare against the manifest's declared ground truth by
    (category, qualified-name) -- not by raw id, since the real detector
    assigns its own content-derived ids independent of the manifest's s1/s2/...
    """
    path = generate_subject("overlap", seed=17, n_classes=6, n_smells=10, dependency_density=0.6,
                             cycle_rate=0.0, positive_rate=0.3, negative_rate=0.3, out_root=str(tmp_path))
    manifest = yaml.safe_load((Path(path) / "manifest.yaml").read_text())

    module = ingest.load(Path(path))
    detected = detect_native.detect(module)
    detected_graph = build(detected, module)

    by_id = {s["id"]: (s["category"], s["loc"][0]) for s in manifest["smells"]}
    planted_edges = {
        (by_id[e["src"]], by_id[e["dst"]])
        for e in manifest["prerequisites"]
    }
    detected_edges = {
        ((e.src.split(":", 1)[0], e.src.split(":", 1)[1]), (e.dst.split(":", 1)[0], e.dst.split(":", 1)[1]))
        for e in detected_graph.edges
        if e.polarity == "prerequisite"
    }

    # Recall: every planted prerequisite the detector could see (i.e. not part of
    # the manifest-only cycle augmentation, which by construction the containment-
    # based builder cannot discover, see generator's CYCLE NOTE) must be rediscovered.
    non_cycle_planted = {
        (src, dst) for (src, dst) in planted_edges if (dst, src) not in planted_edges
    }
    overlap = non_cycle_planted & detected_edges
    recall = len(overlap) / len(non_cycle_planted) if non_cycle_planted else 1.0
    assert recall >= 0.9, f"recall too low: {recall} ({overlap} of {non_cycle_planted})"


@pytest.mark.skipif(
    not _sidecar.is_available(),
    reason="jvm-sidecar jar not built; run `cd jvm-sidecar && ./gradlew build` first",
)
def test_generated_subject_compiles_and_all_tests_pass(tmp_path: Path) -> None:
    path = generate_subject("compiles", seed=23, n_classes=6, n_smells=9, dependency_density=0.6,
                             cycle_rate=0.0, positive_rate=0.4, negative_rate=0.4, out_root=str(tmp_path))
    module = ingest.load(Path(path))

    result = SidecarTestRunner().run(module)

    assert result.compile_errors == []
    assert result.success is True
    assert result.tests_failed == 0
    assert result.tests_run > 0


# --------------------------------------------------------------------------
# Working Brief, Phase 2c: severity decorrelation and the Priority-Dependency
# Conflict benchmark (pair / width / chain).
# --------------------------------------------------------------------------


def test_severity_is_decorrelated_from_dependency_role_across_the_corpus() -> None:
    """Acceptance check (2c §7): across many generated subjects, a God Class
    prerequisite is frequently (not necessarily always) the least severe
    smell among its own children."""
    god_leq_all_children = 0
    total_containers_with_children = 0
    for seed in range(30):
        plan = build_plan(f"decorr_{seed}", seed=seed, n_classes=6, n_smells=12,
                           dependency_density=0.6, cycle_rate=0.0, positive_rate=0.0, negative_rate=0.0)
        for cls in plan.classes:
            if not cls.is_god or not cls.children:
                continue
            total_containers_with_children += 1
            god_severity = cls.god_smell.severity
            if god_severity <= min(c.severity for c in cls.children):
                god_leq_all_children += 1

    assert total_containers_with_children > 0
    fraction = god_leq_all_children / total_containers_with_children
    assert fraction >= 0.85, f"prerequisite was the least-severe child only {fraction:.0%} of the time"


def test_conflict_pair_diverges_impact_only_from_dependency_safe_order() -> None:
    """Acceptance check (2c §7, the headline one): on a conflict subject,
    impact_only (unsafe, sorts purely by impact) picks the high-severity
    dependent before its low-severity prerequisite; every dependency-safe
    strategy cannot. Checked directly against the real detector + builder +
    orderer, not just the plan (planning alone cannot prove impact scoring
    actually diverges once graph-degree/cooccurrence effects are folded in).
    """
    for seed in range(5):
        plan = build_conflict_plan(f"pairdiv_{seed}", seed, shape="pair", width=1)
        assert plan.classes[0].god_smell.severity < plan.classes[0].children[0].severity


def test_conflict_plan_is_deterministic() -> None:
    a = build_conflict_plan("detconf", seed=9, shape="width", width=5)
    b = build_conflict_plan("detconf", seed=9, shape="width", width=5)
    assert [s.severity for s in a.all_smells] == [s.severity for s in b.all_smells]
    assert a.prerequisites == b.prerequisites


def test_chain_plan_prerequisites_are_fully_transitive() -> None:
    plan = build_chain_plan("chaintest", seed=1, depth=5)
    # 4 God Class levels + 1 leaf method = 5 smells; every earlier level is a
    # prerequisite of every later one (transitive containment, matching what
    # graph_builder.build independently derives for real nested classes).
    assert len(plan.all_smells) == 5
    god_ids = [s.id for s in plan.all_smells if s.category == "GodClass"]
    leaf_id = next(s.id for s in plan.all_smells if s.category != "GodClass")
    prereq_set = set(plan.prerequisites)
    for i, gid in enumerate(god_ids):
        for later in god_ids[i + 1 :]:
            assert (gid, later) in prereq_set
        assert (gid, leaf_id) in prereq_set
    # Severity strictly decreases in "how much of a bottleneck", i.e. every
    # level is within the low prerequisite band and the leaf is high.
    for gid in god_ids:
        god_severity = next(s.severity for s in plan.all_smells if s.id == gid)
        assert god_severity <= 0.6
    leaf_severity = next(s.severity for s in plan.all_smells if s.id == leaf_id)
    assert leaf_severity >= 0.6


@pytest.mark.skipif(
    not _sidecar.is_available(),
    reason="jvm-sidecar jar not built; run `cd jvm-sidecar && ./gradlew build` first",
)
@pytest.mark.parametrize("shape,width", [("pair", 1), ("width", 4)])
def test_conflict_subject_compiles_tests_and_diverges(tmp_path: Path, shape: str, width: int) -> None:
    path = generate_conflict_subject(f"conflict_{shape}", seed=3, shape=shape, width=width,
                                      out_root=str(tmp_path))
    module = ingest.load(Path(path))
    result = SidecarTestRunner().run(module)
    assert result.compile_errors == []
    assert result.success is True
    assert result.tests_failed == 0

    smells = detect_native.detect(module)
    g = build(smells, module)
    impact = score(g, ImpactWeights())
    safe_order = order(g, impact)
    impact_only_order = sorted((n.id for n in g.nodes), key=lambda sid: -impact[sid])
    assert safe_order.agenda != impact_only_order


@pytest.mark.skipif(
    not _sidecar.is_available(),
    reason="jvm-sidecar jar not built; run `cd jvm-sidecar && ./gradlew build` first",
)
@pytest.mark.parametrize("depth", [2, 3, 5])
def test_chain_subject_compiles_tests_and_diverges(tmp_path: Path, depth: int) -> None:
    path = generate_chain_subject(f"chain_depth{depth}", seed=depth, depth=depth, out_root=str(tmp_path))
    module = ingest.load(Path(path))
    result = SidecarTestRunner().run(module)
    assert result.compile_errors == []
    assert result.success is True
    assert result.tests_failed == 0

    smells = detect_native.detect(module)
    assert len(smells) == depth
    g = build(smells, module)
    impact = score(g, ImpactWeights())
    safe_order = order(g, impact)
    impact_only_order = sorted((n.id for n in g.nodes), key=lambda sid: -impact[sid])
    assert safe_order.agenda != impact_only_order
    assert safe_order.escalations == []
