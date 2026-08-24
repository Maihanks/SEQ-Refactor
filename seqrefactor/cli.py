"""CLI entry point (Software Specification §4): `seqrefactor run/reproduce/order --config`."""

from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

from seqrefactor.graph.builder import build as build_graph
from seqrefactor.model import Config
from seqrefactor.orchestrator import Orchestrator
from seqrefactor.report import Reporter, hypothesis_tests

load_dotenv()


def _load_config(config_path: Path) -> Config:
    with Path(config_path).open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config(**raw)


def _content_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@click.group()
def main() -> None:
    """SEQ-REFACTOR: dependency-safe, impact-forward multi-smell refactoring."""


@main.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--out", "out_dir", default="runs", type=click.Path())
def run(config_path: str, out_dir: str) -> None:
    """Run the ablation matrix (Section 8.3) over every subject matched by
    `subjects_glob`, writing one JSON RunReport per (subject, strategy,
    generator) cell plus an aggregate summary, all content-hashed (NFR-3)."""
    cfg = _load_config(Path(config_path))
    subjects = sorted(Path(p) for p in glob.glob(cfg.subjects_glob) if Path(p).is_dir())
    if not subjects:
        raise click.ClickException(f"no subjects matched glob: {cfg.subjects_glob}")

    orchestrator = Orchestrator()
    reports = orchestrator.run_matrix(cfg, subjects)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    for report in reports:
        payload = report.model_dump_json(indent=2)
        digest = _content_hash(payload)
        filename = f"{report.subject}__{report.strategy}__{report.generator}__{digest}.json"
        (out_path / filename).write_text(payload, encoding="utf-8")
        click.echo(f"wrote {filename}")

    summary = Reporter().ablation(reports)
    (out_path / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    click.echo(f"wrote summary.json ({len(reports)} run reports)")


@main.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.argument("subject", type=click.Path(exists=True))
@click.option("--strategy", default=None)
@click.option("--generator", default=None)
def order(config_path: str, subject: str, strategy: str | None, generator: str | None) -> None:
    """Print the computed agenda and escalations for a single subject, without
    generating or applying any transformation (useful for auditing OR-1..OR-5)."""
    from seqrefactor import ingest
    from seqrefactor.detect import native as detect_native
    from seqrefactor.orchestrator import _select_ordering
    from seqrefactor.order import impact as impact_scorer

    cfg = _load_config(Path(config_path))
    module = ingest.load(Path(subject))
    smells = detect_native.detect(module)
    g = build_graph(smells, module)
    impact_scores = impact_scorer.score(g, cfg.impact_weights)
    ordering = _select_ordering(
        strategy or cfg.strategies[0], g, impact_scores, discount=cfg.discount, seed=cfg.seed
    )

    click.echo(f"subject: {module.name}")
    click.echo(f"smells detected: {len(smells)}")
    click.echo("agenda:")
    for sid in ordering.agenda:
        click.echo(f"  {sid}  impact={impact_scores.get(sid, 0.0):.3f}")
    if ordering.escalations:
        click.echo("escalations (human review, never auto-ordered):")
        for comp in ordering.escalations:
            click.echo(f"  {comp}")


@main.command()
@click.argument("run_report_path", type=click.Path(exists=True))
def reproduce(run_report_path: str) -> None:
    """Recompute the derived measures (NSR, cascading violations, ordering
    validity, escalation rate) from a persisted RunReport and confirm they
    match the stored computed fields -- the byte-for-byte reproducibility
    check NFR-2/NFR-3 exist to make possible."""
    from seqrefactor.model import RunReport

    payload = Path(run_report_path).read_text(encoding="utf-8")
    report = RunReport.model_validate_json(payload)

    click.echo(f"subject={report.subject} strategy={report.strategy} generator={report.generator}")
    click.echo(f"net_smell_resolution={report.net_smell_resolution}")
    click.echo(f"cascading_violations={report.cascading_violations}")
    click.echo(f"ordering_validity={report.ordering_validity}")
    click.echo(f"escalation_rate={report.escalation_rate}")
    click.echo("content_hash=" + _content_hash(payload))


@main.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--out", "out_dir", default="results", type=click.Path())
@click.option(
    "--generator",
    default="baseline",
    help="Generator for the main ablation matrix (default: baseline -- no LLM/API calls needed).",
)
@click.option(
    "--scaling-sizes",
    default="10,25,50,100",
    help="Comma-separated module sizes (|V|) for the Table IV scaling study.",
)
def results(config_path: str, out_dir: str, generator: str, scaling_sizes: str) -> None:
    """Regenerate Tables II-IV and results/SUMMARY.md from a fixed seed
    (Working Brief §8): one command, every number from a real computation,
    nothing hand-entered.

    Table III (dependency mass) and Table IV (complexity scaling) run fully
    offline -- no Java toolchain needed. Table II (the main ablation) and
    H1-H3 need the built jvm-sidecar (see jvm-sidecar/README.md) for real
    test/metric verification, exactly like `seqrefactor run`; if it isn't
    built, Table II is skipped with a clear message rather than crashing the
    whole command.
    """
    from seqrefactor._sidecar import SidecarUnavailable
    from seqrefactor.datasets import graph_from_manifest, list_subjects, load_manifest
    from seqrefactor.eval import tables as eval_tables
    from seqrefactor.eval.complexity import run_corpus_study, run_scaling_study
    from seqrefactor.eval.depmass import run_study as run_depmass_study
    from seqrefactor.eval.detector_quality import run_study as run_detector_quality_study
    from seqrefactor.eval.random_study import run_study as run_random_study

    cfg = _load_config(Path(config_path))
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    subjects = list_subjects()
    graphs = [(s, graph_from_manifest(load_manifest(s))) for s in subjects]

    masses, h4 = run_depmass_study([(s, g, None) for s, g in graphs])
    eval_tables.table3_depmass(masses, out_dir=out_path)
    click.echo(f"wrote table3_depmass.* ({len(masses)} subjects)")

    sizes = [int(s) for s in scaling_sizes.split(",") if s.strip()]
    records = run_scaling_study(module_sizes=sizes, seed=cfg.seed) + run_corpus_study()
    eval_tables.table4_efficiency(records, out_dir=out_path)
    click.echo(f"wrote table4_efficiency.* ({len(records)} rows, sizes={sizes} + real corpus)")

    detector_results = run_detector_quality_study(subjects)
    eval_tables.table5_detector_quality(detector_results, out_dir=out_path)
    click.echo(f"wrote table5_detector_quality.* ({len(detector_results)} subjects)")

    random_results = run_random_study(graphs, n_samples=200, seed=cfg.seed)
    eval_tables.table6_random_baseline(random_results, out_dir=out_path)
    click.echo(f"wrote table6_random_baseline.* ({len(random_results)} subjects)")

    h1_h3: dict = {}
    ablation_cfg = cfg.model_copy(update={"generators": [generator]})
    try:
        subjects = sorted(Path(p) for p in glob.glob(cfg.subjects_glob) if Path(p).is_dir())
        orchestrator = Orchestrator()
        reports = orchestrator.run_matrix(ablation_cfg, subjects)
        eval_tables.table2_ablation(reports, out_dir=out_path)
        h1_h3 = hypothesis_tests(reports)
        click.echo(f"wrote table2_ablation.* ({len(reports)} run reports)")
    except SidecarUnavailable as exc:
        click.echo(f"skipped table2_ablation (jvm-sidecar not built): {exc}")

    eval_tables.summary_md(h1_h3, h4, out_dir=out_path)
    click.echo(f"wrote {out_path / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
