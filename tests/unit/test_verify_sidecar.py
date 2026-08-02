"""Unit tests for the sidecar-backed verifier components (§5.8): the JUnit test
runner and the five-family metric facade's CK half. Skipped if the jvm-sidecar
jar has not been built (see jvm-sidecar/README.md)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seqrefactor import _sidecar, ingest
from seqrefactor.model import Module
from seqrefactor.verify.metrics import MetricFacade
from seqrefactor.verify.tests import NoTestRootError, SidecarTestRunner

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets" / "synthetic"

pytestmark = pytest.mark.skipif(
    not _sidecar.is_available(),
    reason="jvm-sidecar jar not built; run `cd jvm-sidecar && ./gradlew build` first",
)


def test_sidecar_test_runner_reports_pass_on_pilot_module() -> None:
    module = ingest.load(DATASETS_DIR / "pilot_checkout_v1")
    result = SidecarTestRunner().run(module)
    assert result.success is True
    assert result.tests_run == 4
    assert result.tests_failed == 0


def test_sidecar_test_runner_requires_main_and_test_dirs() -> None:
    module = Module(name="no-dirs", path=DATASETS_DIR)
    with pytest.raises(NoTestRootError):
        SidecarTestRunner().run(module)


def test_metric_facade_reports_zero_delta_for_identical_snapshots() -> None:
    module = ingest.load(DATASETS_DIR / "pilot_checkout_v1")
    delta = MetricFacade().deltas(module, module, loc=["orders.OrderService.checkout"])
    assert delta.coupling == 0.0
    assert delta.complexity == 0.0
    assert delta.cohesion == 0.0
