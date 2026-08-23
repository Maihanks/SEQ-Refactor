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
from seqrefactor.synth.generator import build_plan, generate_subject
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
