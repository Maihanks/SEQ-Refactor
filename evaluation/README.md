# evaluation/ — real, committed results (Tables II, III, IV)

Deliberately **not** named `results/`/`runs/` (both gitignored elsewhere in this repo as
regenerable output) — this directory holds specific, committed snapshots that back numbers
written into the paper. Regenerating any of these (commands below) is deterministic and seeded,
but treat new output as superseding this snapshot rather than assuming a byte-for-byte match —
wall-clock timings in particular are hardware-dependent.

**Table-numbering note**: this repo's own code (`eval/tables.py`) names its three output files
`table2_ablation`, `table3_depmass`, `table4_efficiency`, following the Working Brief's original
(Phase 1) file-naming convention. If you're cross-referencing against paper prose that calls these
Tables IV/V/VI (a different, later numbering scheme used in a Phase-2-adjacent paper-writing
session), the mapping is: `table2_ablation` = main ablation, `table3_depmass` = dependency-mass
(RQ5/H4), `table4_efficiency` = complexity-scaling (RQ6/H5) — same three studies, two different
numbering conventions layered on top of the same underlying files.

## Phase 2 update (2026-08-23): the powered, multi-subject study

Everything below this point was regenerated against the Working Brief Phase 2 corpus: 15
generated subjects (`seqrefactor/synth/generator.py`, `datasets/synthetic/CORPUS.md`) plus the 3
pre-existing hand-written synthetic subjects (2 of which have no real Java source and contribute
empty runs) = 18 subjects, 5 ordering strategies (`seqrefactor`, `impact_only`, `topo_only`,
`unordered`, `search_based`), baseline generator only (no `OPENAI_API_KEY` in this environment),
`max_steps=10` per (subject, strategy) run. Raw run reports are committed verbatim under
`datasets/synthetic/example_run/` (90 `RunReport` JSON files + `summary.json`), the same
regenerable-snapshot pattern as `datasets/opensource/json_java_v1/example_run/`.

### Table II — main ablation (RQ1-RQ4, H1-H3)

**Command:** `uv run seqrefactor run --config <config with subjects_glob pointed at a scratch
copy of the corpus>` (see REPRODUCE.md step 4), then `eval_tables.table2_ablation(reports)`.

**H1-H3, real statistics, n=18 (no longer "insufficient data"):**

| Hypothesis | Supported | n | p-value | effect size (r) | note |
|---|---|---|---|---|---|
| H1 (fewer cascading violations vs. unordered) | insufficient data | 18 | n/a | n/a | every paired difference is exactly zero: the test is degenerate |
| H2 (higher NSR vs. unordered) | insufficient data | 18 | n/a | n/a | every paired difference is exactly zero: the test is degenerate |
| H2 (higher NSR vs. topo_only) | insufficient data | 18 | n/a | n/a | every paired difference is exactly zero: the test is degenerate |
| H3 (higher AUC vs. topo_only) | **no** | 18 | 0.264 | 0.286 | not supported at p<0.05 |

**What actually happened, honestly, not smoothed over**: `net_smell_resolution` is 0 for
`seqrefactor`, `topo_only`, `unordered`, and `search_based` on *every one* of the 18 subjects
(hence H1/H2 being degenerate, not merely non-significant — there is no variance to test). The
mechanism, traced through the raw `RunReport` steps: the deterministic baseline generator cannot
produce a patch for a class-level smell at all (`generate/baseline.py` only wraps method bodies),
and every generated subject's dependency-respecting strategies visit their GodClass(es) first, so
most of the `max_steps=10` budget on multi-GodClass subjects is spent on doomed
`"generator produced no patch"` rejections before any method-level smell is even reached — the
exact same mechanism already documented for the single-subject Phase 1 run against
`datasets/opensource/json_java_v1`, now confirmed to generalise across the whole corpus.

`impact_only` is the one strategy with non-zero cascading violations (10 total, concentrated in a
single subject — see below), which is *why* H1/H2 (both comparing safe strategies against
`unordered`, which also happens to show 0 violations) come out degenerate: the real safety
signal in this corpus is `seqrefactor`/`topo_only`/`search_based`/`unordered` vs. `impact_only`,
not vs. each other. `report.hypothesis_tests` does not currently include an
H1-vs-`impact_only` comparison; that would be the more informative pairing for a future revision
of `report.py`, not something to retrofit into this snapshot's numbers.

**Where `impact_only`'s violations came from**: `pilot_checkout_v1` (the *hand-written* Phase 1
subject, not one of the 15 generated ones) — `impact_only` reaches
`BigSwitch:orders.OrderService.dispatchStatus` directly, without its `GodClass:OrderService`
prerequisite ever being accepted, and the baseline generator's repeated wrap-and-reintroduce
pattern (`dispatchStatus` -> `dispatchStatusExtracted` -> `dispatchStatusExtractedExtracted` ->
...) makes every one of its 10 steps a cascading violation. **None of the 15 generated subjects
show this failure mode under `impact_only`** — a real, honest limitation of the current generator
worth stating plainly: `synth/generator.py`'s `_SEVERITY_BASE` always assigns `GodClass` the
highest severity (1.0) of any category, and `GodClass` vertices also have the highest
co-occurrence degree in the dependency graph (they're connected to every child they contain) —
between those two terms of the impact score (paper Eq. 1), `GodClass` ends up impact-dominant by
construction, so `impact_only` (impact-first, topology stripped) still visits it first almost by
coincidence, and the failure mode `impact_only` is specifically designed to expose rarely
triggers. Varying severity assignment (e.g. sometimes giving a method-level smell higher severity
than its containing class) is the natural next change to `synth/generator.py` if a future run
needs the generated corpus itself to exercise this failure mode, not just the one hand-written
fixture.

`search_based` matched `seqrefactor`'s outcome on every subject in this run (0 cascading
violations, 0 NSR) — expected, since with the baseline generator producing no usable patch for
any GodClass, the choice of *which* safe ordering to search for barely matters when the very first
action in that ordering fails regardless of which safe ordering was chosen.

### Table III — dependency-mass study (RQ5, H4)

**Command:** see REPRODUCE.md step 5 (now threading the real `seqrefactor` `RunReport` for each
subject through `run_study`, not `None`).

**H4, real statistic, n=18:** `statistic=32.0, p=0.827, effect_size_r=-0.297, supported=False`
("not supported at p<0.05"). `co_resolution_events` and `cascading_violation_events` are 0 for
every subject in this run, for the same reason Table II's NSR is 0 everywhere: nothing got net
resolved within the 10-step, baseline-generator-limited budget, so no injected
positive/negative-dependency pair was ever actually realised. The *structural* mass itself (from
each subject's manifest ground truth, independent of any run) is real and non-degenerate — see
`table3_depmass.csv` for all 18 rows; positive/negative mass varies subject to subject (e.g.
`synth_xlarge_medium`: 1.71 positive / 1.18 negative; several small subjects: 0.0 / 0.0, since not
every generated subject's random draw happened to inject a signed dependency at all).

**HONESTY NOTE carried forward unchanged from Phase 1**: the probabilities behind this mass are
illustrative catalogue/generator defaults, not mined data — see `graph/rules.py` and
`synth/generator.py`'s own notes.

### Table IV — complexity-scaling study (RQ6, H5)

Two complementary measurements, both in `table4_efficiency.csv` (334 rows total), distinguished by
the `subject` column (`synthetic_V<n>` for the sweep, real subject names for the corpus):

**1. Synthetic |V| sweep** (unchanged from Phase 1, 88 rows): from-scratch/incremental edge-touch
ratio grows from ~8x at |V|=10 to ~10,600x at |V|=200 — see Phase 1 section below for the full
table (kept for reference).

**2. Real corpus** (new, Phase 2, 246 rows, `eval/complexity.run_corpus_study`, up to 10 steps per
subject): the same trend, on real subject graphs rather than a synthetic sweep --

| subject | total from-scratch edge_touches | total incremental edge_touches | ratio |
|---|---|---|---|
| synth_small_low | 39 | 3 | 13.0x |
| synth_small_medium | 57 | 5 | 11.4x |
| synth_small_high | 84 | 5 | 16.8x |
| synth_medium_low | 172 | 7 | 24.6x |
| synth_medium_medium | 291 | 9 | 32.3x |
| synth_medium_high | 438 | 13 | 33.7x |
| synth_large_low | 809 | 11 | 73.6x |
| synth_large_medium | 1190 | 14 | 85.0x |
| synth_large_high | 1778 | 18 | 98.8x |
| synth_xlarge_medium | 2966 | 23 | **129.0x** |

The size-tier ordering (small < medium < large < xlarge) tracks the ratio almost exactly,
corroborating the synthetic sweep's asymptotic claim on independently-generated real graphs, not
just the controlled sweep. Every row's underlying equivalence (incremental == from-scratch, the
actual H5 claim) is proven by construction and enforced by
`tests/property/test_incremental_equivalence.py`, run against this same corpus among others.

## Phase 1 results (superseded scope, kept for reference)

The original single/few-subject numbers this section used to report (n=3 synthetic subjects for
Table III with `co_resolution_events`/`cascading_violation_events` always 0 by construction since
no run was threaded through; a 5-point |V| sweep for Table IV) are still present as the
`synthetic_V*`-tagged rows and the `billing_cycle_v1`/`notification_mixed_v1`/`pilot_checkout_v1`
rows in the current CSVs — nothing from Phase 1 was deleted, Phase 2 only added subjects and
threaded real run data through where Phase 1 had left it structural-only.
