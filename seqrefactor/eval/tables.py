"""Table II/III/IV emission and results/SUMMARY.md (Working Brief §8: "make it
trivial to replace the paper's [RESULTS PENDING] markers with real, current
numbers" -- see REPO_MAP.md §3 for why the paper on disk does not currently
have such markers; this module exists so it can adopt them without further
plumbing work whenever it does).

Every table is emitted three ways to ``results/``: CSV (data of record), LaTeX
(``\\begin{table}...``, for an IEEE build), and Markdown (for quick review).
Every row comes from a real computation upstream (``report.py``,
``eval/depmass.py``, ``eval/complexity.py``) -- nothing here computes a
reported number itself, it only formats one.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from seqrefactor.eval.depmass import H4Result
from seqrefactor.eval.detector_quality import DetectorQualityResult
from seqrefactor.eval.random_study import RandomBaselineResult
from seqrefactor.eval.stats import PairedTestResult
from seqrefactor.model import ComplexityRecord, DependencyMass, RunReport
from seqrefactor.report import ablation_table

RESULTS_DIR = Path("results")


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(rows: list[dict[str, Any]], path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("_no rows_")
    else:
        fieldnames = list(rows[0].keys())
        lines.append("| " + " | ".join(fieldnames) + " |")
        lines.append("| " + " | ".join("---" for _ in fieldnames) + " |")
        for row in rows:
            lines.append("| " + " | ".join(str(row[f]) for f in fieldnames) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _latex_escape(value: str) -> str:
    return value.replace("_", "\\_").replace("%", "\\%")


def _write_latex(rows: list[dict[str, Any]], path: Path, caption: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("% no rows\n", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{'l' * len(fieldnames)}}}",
        "\\toprule",
        " & ".join(_latex_escape(f) for f in fieldnames) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_latex_escape(str(row[f])) for f in fieldnames) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit_table(
    rows: list[dict[str, Any]], stem: str, caption: str, label: str, out_dir: Path = RESULTS_DIR
) -> list[dict[str, Any]]:
    """Emit ``rows`` as ``{stem}.csv``, ``{stem}.tex``, ``{stem}.md`` under ``out_dir``."""
    _write_csv(rows, out_dir / f"{stem}.csv")
    _write_latex(rows, out_dir / f"{stem}.tex", caption, label)
    _write_markdown(rows, out_dir / f"{stem}.md", caption)
    return rows


def table2_ablation(runs: list[RunReport], out_dir: Path = RESULTS_DIR) -> list[dict[str, Any]]:
    rows = [dict(cell) for cell in ablation_table(runs)]
    return emit_table(rows, "table2_ablation", "SEQ-REFACTOR ablation (RQ1-RQ4)", "tab:ablation", out_dir)


def table3_depmass(masses: list[DependencyMass], out_dir: Path = RESULTS_DIR) -> list[dict[str, Any]]:
    rows = [
        {
            "subject": m.subject,
            "positive_mass": round(m.positive_mass, 4),
            "negative_mass": round(m.negative_mass, 4),
            "mass_ratio": round(m.mass_ratio, 4),
            "co_resolution_events": m.co_resolution_events,
            "cascading_violation_events": m.cascading_violation_events,
        }
        for m in masses
    ]
    return emit_table(
        rows, "table3_depmass", "Dependency-mass study (RQ5, H4)", "tab:depmass", out_dir
    )


def table4_efficiency(
    records: list[ComplexityRecord], out_dir: Path = RESULTS_DIR
) -> list[dict[str, Any]]:
    rows = [
        {
            "subject": r.subject,
            "step_index": r.step_index,
            "strategy": r.strategy,
            "module_size": r.module_size,
            "vertex_touches": r.counters.vertex_touches,
            "edge_touches": r.counters.edge_touches,
            "heap_operations": r.counters.heap_operations,
            "order_renumbering_operations": r.counters.order_renumbering_operations,
            "wall_clock_seconds": round(r.wall_clock_seconds, 8),
        }
        for r in records
    ]
    return emit_table(
        rows,
        "table4_efficiency",
        "Incremental vs. from-scratch maintenance cost (RQ6, H5)",
        "tab:efficiency",
        out_dir,
    )


def table5_detector_quality(
    results: list[DetectorQualityResult], out_dir: Path = RESULTS_DIR
) -> list[dict[str, Any]]:
    rows = [
        {
            "subject": r.subject,
            "ground_truth_count": r.ground_truth_count,
            "detected_count": r.detected_count,
            "true_positives": r.true_positives,
            "precision": r.precision,
            "recall": r.recall,
            "f1": r.f1,
        }
        for r in results
    ]
    return emit_table(
        rows,
        "table5_detector_quality",
        "Detector precision/recall/F1 against planted ground truth",
        "tab:detector-quality",
        out_dir,
    )


def table6_random_baseline(
    results: list[RandomBaselineResult], out_dir: Path = RESULTS_DIR
) -> list[dict[str, Any]]:
    rows = [
        {
            "subject": r.subject,
            "n_samples": r.n_samples,
            "mean_violation_fraction": r.mean_violation_fraction,
            "stdev_violation_fraction": r.stdev_violation_fraction,
            "mean_random_topological_objective": r.mean_random_topological_objective,
            "stdev_random_topological_objective": r.stdev_random_topological_objective,
            "seqrefactor_objective": r.seqrefactor_objective,
        }
        for r in results
    ]
    return emit_table(
        rows,
        "table6_random_baseline",
        "Random / random-topological reference statistics (mean and spread across samples)",
        "tab:random-baseline",
        out_dir,
    )


def _fmt(value: float | None) -> str:
    return f"{value:.4g}" if value is not None else "n/a"


def _verdict(supported: bool | None) -> str:
    if supported is True:
        return "yes"
    if supported is False:
        return "no"
    return "insufficient data"


def summary_md(
    h1_h3: dict[str, PairedTestResult], h4: H4Result, out_dir: Path = RESULTS_DIR
) -> None:
    """results/SUMMARY.md (Working Brief §8): "states, for each of H1 to H5,
    whether the current data support it, with the key statistic. This is what
    to read before updating the paper."."""
    lines = [
        "# SEQ-REFACTOR results summary",
        "",
        "Read this before updating any paper claim with a number from `results/`.",
        "",
        "| Hypothesis | Supported | n | p-value | effect size (r) | note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, result in h1_h3.items():
        lines.append(
            f"| {name} | {_verdict(result.supported)} | {result.n} | "
            f"{_fmt(result.p_value)} | {_fmt(result.effect_size_r)} | {result.note} |"
        )
    lines.append(
        f"| H4_dependency_mass | {_verdict(h4.supported)} | {h4.n} | "
        f"{_fmt(h4.p_value)} | {_fmt(h4.effect_size_r)} | {h4.note} |"
    )
    h5_note = (
        "H5 (incremental maintenance is bit-for-bit identical to a from-scratch "
        "rebuild) is not a statistical hypothesis: it is guaranteed by construction "
        "(see `seqrefactor/graph/incremental.py`'s design note) and enforced by "
        "`tests/property/test_incremental_equivalence.py`, which must pass for any "
        "number in `table4_efficiency` to be trustworthy."
    )
    honesty_note = (
        "HONESTY NOTE: H4's dependency-mass inputs are seeded catalogue defaults "
        "(`seqrefactor/graph/rules.py`), not mined from version history -- see that "
        "module's docstring. RQ4's weight-sensitivity sweep "
        "(`seqrefactor/eval/weight_sweep.py`) and the open-source subject tier with "
        "mined reference orders (paper Section VII-C) remain out of scope for this "
        "increment; see REPO_MAP.md."
    )
    lines += ["", h5_note, "", honesty_note]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
