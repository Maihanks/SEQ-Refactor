"""Module ingest and the coverage precondition (Software Specification §5.1, FR-1).

A module that fails the coverage precondition is excluded, not refactored on
a weak oracle: without adequate test coverage the Verifier's test signal
(seqrefactor.verify.tests) cannot be trusted to catch a behaviour-changing
transformation, so the pipeline must not proceed past S1 (Detect).
"""

from __future__ import annotations

import csv
from pathlib import Path

from seqrefactor import _treesitter as ts
from seqrefactor.model import Module, PreconditionReport

_MAIN_LAYOUTS = ("src/main/java", "src")
_TEST_LAYOUTS = ("src/test/java", "test")


def _first_existing(root: Path, candidates: tuple[str, ...]) -> Path | None:
    for rel in candidates:
        candidate = root / rel
        if candidate.is_dir():
            return candidate
    return None


def load(path: Path, classpath: list[Path] | None = None) -> Module:
    """Load a Java module's source and test file layout (Maven/Gradle-style convention)."""
    root = Path(path)
    main_dir = _first_existing(root, _MAIN_LAYOUTS) or root
    test_dir = _first_existing(root, _TEST_LAYOUTS)

    source_files = sorted(main_dir.rglob("*.java")) if main_dir.is_dir() else []
    test_files = sorted(test_dir.rglob("*.java")) if test_dir and test_dir.is_dir() else []
    # If no dedicated main/ layout was found, main_dir fell back to the module root, which
    # would otherwise double-count files already claimed by test_dir.
    if test_dir is not None:
        source_files = [f for f in source_files if test_dir not in f.parents]

    return Module(
        name=root.name,
        path=root,
        source_files=source_files,
        test_files=test_files,
        main_dir=main_dir,
        test_dir=test_dir,
        classpath=classpath or [],
    )


def _jacoco_csv_coverage(report_path: Path) -> float | None:
    """Parse a standard `jacoco:report` CSV (INSTRUCTION_MISSED/INSTRUCTION_COVERED columns)."""
    if not report_path.is_file():
        return None
    covered = 0
    missed = 0
    with report_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            covered += int(row.get("INSTRUCTION_COVERED", 0) or 0)
            missed += int(row.get("INSTRUCTION_MISSED", 0) or 0)
    total = covered + missed
    return covered / total if total else None


def _heuristic_coverage(module: Module) -> float:
    """Test-method-to-production-method ratio, capped at 1.0.

    A proxy used only when no JaCoCo report is available: it counts `@Test`
    occurrences in test sources against the number of methods tree-sitter
    finds in production sources. This is deliberately conservative and
    coarse -- it is not a substitute for instruction/branch coverage, and
    Module.coverage should be overridden with a real report whenever one
    exists (see `_jacoco_csv_coverage`).
    """
    if not module.source_files:
        return 0.0
    production_methods = sum(len(c.methods) for c in ts.parse_module(module.source_files))
    if production_methods == 0:
        return 1.0
    test_method_count = sum(
        f.read_text(encoding="utf-8", errors="replace").count("@Test") for f in module.test_files
    )
    return min(1.0, test_method_count / production_methods)


def check_preconditions(
    module: Module,
    coverage_min: float = 0.80,
    jacoco_report: Path | None = None,
) -> PreconditionReport:
    coverage = None
    if jacoco_report is not None:
        coverage = _jacoco_csv_coverage(jacoco_report)
    if coverage is None:
        default_report = module.path / "coverage" / "jacoco.csv"
        coverage = _jacoco_csv_coverage(default_report)
    if coverage is None:
        coverage = _heuristic_coverage(module)

    reasons: list[str] = []
    if not module.source_files:
        reasons.append("no .java source files found under the module path")
    if coverage < coverage_min:
        reasons.append(f"coverage {coverage:.1%} is below the {coverage_min:.0%} precondition")

    return PreconditionReport(
        coverage=coverage,
        coverage_min=coverage_min,
        passed=not reasons,
        reasons=reasons,
    )
