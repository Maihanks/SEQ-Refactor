"""Integration / end-to-end tests (§9.3).

Golden end-to-end: the full pipeline (detect -> build -> order -> retrieve ->
generate -> verify -> gate -> re-detect) runs on a real synthetic subject with
the deterministic baseline generator (no network, no API key) and produces a
well-formed, internally consistent RunReport. Every test here operates on a
throwaway copy of the dataset (tmp_path), never the checked-in fixture --
the orchestrator's job is to mutate its target module in place, so pointing
it at the real datasets/ directory would corrupt the ground-truth fixture.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from seqrefactor import _sidecar
from seqrefactor.model import Config
from seqrefactor.orchestrator import Orchestrator

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets" / "synthetic"

pytestmark = pytest.mark.skipif(
    not _sidecar.is_available(),
    reason="jvm-sidecar jar not built; run `cd jvm-sidecar && ./gradlew build` first",
)


@pytest.fixture
def pilot_copy(tmp_path: Path) -> Path:
    dest = tmp_path / "pilot_checkout_v1"
    shutil.copytree(DATASETS_DIR / "pilot_checkout_v1", dest)
    return dest


def test_end_to_end_run_produces_consistent_run_report(pilot_copy: Path) -> None:
    cfg = Config(
        subjects_glob=str(pilot_copy),
        strategies=["seqrefactor"],
        generators=["baseline"],
        coverage_min=0.0,
        seed=20260101,
    )
    report = Orchestrator().run_one(pilot_copy, cfg, max_steps=3)

    assert report.subject == pilot_copy.name
    assert report.strategy == "seqrefactor"
    assert report.generator == "baseline"
    assert len(report.steps) == 3
    # Every step index is sequential starting at 0 (S1..S7 executed once per step).
    assert [s.index for s in report.steps] == [0, 1, 2]
    # Derived measures are computable and internally consistent (§6 "keep derived
    # quantities derived").
    assert 0.0 <= report.ordering_validity <= 1.0
    assert report.cascading_violations >= 0
    assert isinstance(report.net_smell_resolution, int)


def test_god_class_is_ordered_before_its_method_level_smells(pilot_copy: Path) -> None:
    """OR-1 as exercised through the real detector + builder + orderer + orchestrator,
    not just the golden test's manifest-driven ground truth (§9.1 "on a synthetic
    subject the built graph matches the manifest's prerequisite edges")."""
    from seqrefactor import ingest
    from seqrefactor.detect import native as detect_native
    from seqrefactor.graph.builder import build
    from seqrefactor.order import impact as impact_scorer
    from seqrefactor.order.orderer import order

    module = ingest.load(pilot_copy)
    smells = detect_native.detect(module)
    g = build(smells, module)
    impact_scores = impact_scorer.score(g, Config(subjects_glob="x").impact_weights)
    ordering = order(g, impact_scores)

    god_class_id = next(s.id for s in smells if s.category == "GodClass")
    pos = {sid: i for i, sid in enumerate(ordering.agenda)}
    assert pos[god_class_id] == 0  # every other smell is contained within it


def test_rejected_candidate_leaves_module_untouched(pilot_copy: Path, monkeypatch) -> None:
    """A candidate that fails verification must not mutate the real module (NFR-1)."""
    from seqrefactor.gate import Gate
    from seqrefactor.model import Verdict

    original = (pilot_copy / "src/main/java/orders/OrderService.java").read_text(encoding="utf-8")

    def always_reject(self, smell, evidence):
        return Verdict(smell=smell, accepted=False, rationale="forced rejection for this test")

    monkeypatch.setattr(Gate, "decide", always_reject)

    cfg = Config(subjects_glob=str(pilot_copy), coverage_min=0.0, seed=1)
    Orchestrator().run_one(pilot_copy, cfg, strategy="seqrefactor", generator="baseline", max_steps=2)

    after = (pilot_copy / "src/main/java/orders/OrderService.java").read_text(encoding="utf-8")
    assert after == original
