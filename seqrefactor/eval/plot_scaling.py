"""Regenerate the scaling figure (paper Fig. 5) and its labelled numeric summary
from the committed efficiency table (Working Brief, Phase 3c, G1/G3).

Reads ``evaluation/table4_efficiency.csv`` (repo-internal "Table IV"; paper
Table VII -- see the numbering note in REPRODUCE.md) and writes, deterministically,
from that CSV alone:

- ``evaluation/fig_scaling.png`` / ``.pdf`` -- log-log per-step edge derivations
  vs. module size, from-scratch and incremental series, with a dashed O(V^2)
  reference line anchored to the from-scratch value at V = 100.
- ``evaluation/scaling_summary.md`` -- the step-0 and session-mean edge-derivation
  values at V = 200, clearly labelled (G3): a reader who opens the CSV and sees
  38,416 in the first V = 200 row is not looking at a different number from the
  paper's cited "about 31,816" -- they are looking at the FIRST STEP of the same
  session whose MEAN is 31,816. Both are real, both are correct, and the label
  is what removes the apparent contradiction.

This script computes nothing that is not already in the CSV; it aggregates and
presents. Run it with ``make scaling`` or directly:

    uv run python -m seqrefactor.eval.plot_scaling
"""

from __future__ import annotations

import collections
import csv
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_CSV = Path("evaluation/table4_efficiency.csv")
DEFAULT_OUT_STEM = Path("evaluation/fig_scaling")
DEFAULT_SUMMARY = Path("evaluation/scaling_summary.md")
ANCHOR_MODULE_SIZE = 100
HEADLINE_MODULE_SIZE = 200


def _load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def aggregate_by_module_size(rows: list[dict[str, str]]) -> dict[int, dict[str, list[float]]]:
    by: dict[int, dict[str, list[float]]] = collections.defaultdict(
        lambda: {"from_scratch": [], "incremental": []}
    )
    for r in rows:
        size = int(r["module_size"])
        strategy = r["strategy"]
        if strategy in ("from_scratch", "incremental"):
            by[size][strategy].append(float(r["edge_touches"]))
    return by


def plot(rows: list[dict[str, str]], out_stem: Path = DEFAULT_OUT_STEM) -> Path:
    by = aggregate_by_module_size(rows)
    sizes = sorted(v for v in by if by[v]["from_scratch"] and by[v]["incremental"])
    if not sizes:
        raise ValueError("no module size has both from_scratch and incremental rows")

    fs_mean = [statistics.mean(by[v]["from_scratch"]) for v in sizes]
    inc_mean = [statistics.mean(by[v]["incremental"]) for v in sizes]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.loglog(sizes, fs_mean, marker="o", label="from-scratch", color="#1f4e79")
    ax.loglog(sizes, inc_mean, marker="s", label="incremental", color="#c0392b")

    if ANCHOR_MODULE_SIZE in sizes:
        anchor_value = fs_mean[sizes.index(ANCHOR_MODULE_SIZE)]
    else:
        # Anchor to the from-scratch curve itself if V=100 has no exact row,
        # via its own O(V^2) fit at the nearest size, so the reference line
        # still passes through real data rather than an invented point.
        nearest = min(sizes, key=lambda v: abs(v - ANCHOR_MODULE_SIZE))
        anchor_value = fs_mean[sizes.index(nearest)] * (ANCHOR_MODULE_SIZE / nearest) ** 2
    reference = [anchor_value * (v / ANCHOR_MODULE_SIZE) ** 2 for v in sizes]
    ax.loglog(
        sizes,
        reference,
        linestyle="--",
        color="#7f8c8d",
        label=f"O(V^2) reference (anchored at V={ANCHOR_MODULE_SIZE})",
    )

    ax.set_xlabel("module size |V|")
    ax.set_ylabel("mean edge derivations per step")
    ax.set_title("Smell-dependency graph maintenance:\nfrom-scratch vs. incremental", fontsize=11)
    ax.legend()
    ax.grid(True, which="both", linestyle=":", linewidth=0.5)
    fig.tight_layout()

    out_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = out_stem.with_suffix(".png")
    pdf_path = out_stem.with_suffix(".pdf")
    fig.savefig(png_path, dpi=200)
    # Suppress the PDF backend's embedded creation timestamp: without this, re-running
    # this script on unchanged data produces a byte-different .pdf (though visually
    # identical), which contradicts "regenerates ... deterministically" above.
    fig.savefig(pdf_path, metadata={"CreationDate": None})
    plt.close(fig)
    return png_path


def summary(rows: list[dict[str, str]], module_size: int = HEADLINE_MODULE_SIZE) -> dict[str, float]:
    """The G3 labelled pair: step-0 (all-pairs, first step of the session) and
    session-mean (averaged over every step as the graph shrinks) edge-derivation
    counts for ``module_size``, read directly from the CSV rows -- never hand-entered."""
    from_scratch = sorted(
        (
            (int(r["step_index"]), float(r["edge_touches"]))
            for r in rows
            if r["strategy"] == "from_scratch" and int(r["module_size"]) == module_size
        ),
        key=lambda pair: pair[0],
    )
    if not from_scratch:
        raise ValueError(f"no from_scratch rows for module_size={module_size}")

    step0_value = from_scratch[0][1]
    session_mean = statistics.mean(value for _, value in from_scratch)
    return {
        f"edge_derivations_step0_V{module_size}": step0_value,
        f"edge_derivations_session_mean_V{module_size}": session_mean,
        f"session_steps_V{module_size}": float(len(from_scratch)),
    }


def write_summary(rows: list[dict[str, str]], out_path: Path = DEFAULT_SUMMARY) -> Path:
    stats = summary(rows)
    step0_key = f"edge_derivations_step0_V{HEADLINE_MODULE_SIZE}"
    mean_key = f"edge_derivations_session_mean_V{HEADLINE_MODULE_SIZE}"
    steps_key = f"session_steps_V{HEADLINE_MODULE_SIZE}"

    lines = [
        "# Scaling study summary (Fig. 5 companion, Working Brief Phase 3c G3)",
        "",
        "Regenerated by `seqrefactor/eval/plot_scaling.py` from "
        "`evaluation/table4_efficiency.csv` alone -- never hand-edited.",
        "",
        f"At module size V = {HEADLINE_MODULE_SIZE}, from-scratch strategy, over a "
        f"{int(stats[steps_key])}-step session:",
        "",
        f"- **Step-0 (first-step, all-pairs) edge derivations**: "
        f"`{step0_key}` = {stats[step0_key]:,.0f}. This is the cost of the very "
        f"first rebuild, before any smell has been resolved: all pairs of the "
        f"surviving smells at that instant.",
        f"- **Session-mean edge derivations**: `{mean_key}` = {stats[mean_key]:,.0f}. "
        f"This is the mean over every step of the session; it is smaller than the "
        f"step-0 value because the graph shrinks as smells resolve, so later steps "
        f"have fewer surviving pairs to re-derive.",
        "",
        "These are two different quantities over the same session, not two "
        "measurements of the same thing -- a reader who sees a different value in "
        "the first V=200 row of `table4_efficiency.csv` (the step-0 value) than in "
        "a paper sentence citing the session mean is not looking at an error.",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def main(csv_path: Path = DEFAULT_CSV) -> None:
    rows = _load_rows(csv_path)
    png_path = plot(rows)
    summary_path = write_summary(rows)
    stats = summary(rows)
    print(f"wrote {png_path} (+ .pdf)")
    print(f"wrote {summary_path}")
    for key, value in stats.items():
        print(f"  {key} = {value:,.2f}")


if __name__ == "__main__":
    main()
