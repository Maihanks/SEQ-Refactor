"""Unit tests for the deterministic Extract-Method baseline generator (§5.7)."""

from __future__ import annotations

from pathlib import Path

from seqrefactor import ingest
from seqrefactor.generate.baseline import refactor
from seqrefactor.model import GenContext, SmellInstance

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets" / "synthetic"


def _pilot_module():
    return ingest.load(DATASETS_DIR / "pilot_checkout_v1")


def test_refactor_wraps_target_method_and_forwards_arguments() -> None:
    module = _pilot_module()
    target = SmellInstance(id="s2", category="LongMethod", loc=["orders.OrderService.checkout"])

    candidate = refactor(target, GenContext(target="s2"), module, seed=7)

    assert candidate.generator == "baseline"
    assert candidate.seed == 7
    assert "checkoutExtracted(order)" in candidate.patch
    assert "public String checkout(Order order)" in candidate.patch


def test_refactor_is_deterministic_across_calls() -> None:
    module = _pilot_module()
    target = SmellInstance(id="s3", category="LongMethod", loc=["orders.OrderService.applyDiscount"])

    first = refactor(target, GenContext(target="s3"), module, seed=1)
    second = refactor(target, GenContext(target="s3"), module, seed=1)

    assert first.patch == second.patch


def test_refactor_is_noop_for_class_level_smell() -> None:
    module = _pilot_module()
    target = SmellInstance(id="s1", category="GodClass", loc=["orders.OrderService"])

    candidate = refactor(target, GenContext(target="s1"), module, seed=1)

    assert candidate.patch == ""
