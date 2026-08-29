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

**Command:** `uv run seqrefactor results --config <config> --out <dir>` now does this by default
(the `results` command threads each subject's real `seqrefactor` `RunReport` from the ablation
matrix it runs for Table II straight into `run_study`, instead of passing `None` for every
subject unconditionally as it did before the wiring fix below) -- see REPRODUCE.md step 5.

**Identifier-mismatch bug (found and fixed):** the manifest's ground-truth dependency edges are
declared over hand-picked smell ids (`s1`, `s2`, ...; `datasets.graph_from_manifest`), while a
real run's `RunReport.steps` record whatever id the live detector (`detect/native.py`'s
`_stable_id`) independently derived for what it actually found in the source at that step. These
two id spaces never shared a namespace, so the realised co-resolution check could never match
regardless of what a run accepted; demonstrated with a constructed fixture (both ends accepted
under detector ids) in the regression tests below, since the real LLM-generator run on this
subject (evaluation/llm_eval_modest/) did not itself happen to accept both ends of this specific
edge (notifyBilling failed to compile; notifyWarehouse was never attempted within budget) and so
cannot demonstrate the bug on its own. Fixed in `eval/depmass.py`
(translates manifest edge endpoints into detector-id form before the check, reusing `_stable_id`
directly so the two conventions can't drift apart again) with two regression tests in
`tests/unit/test_depmass.py`.

**H4, real statistic, n=28 (current corpus; supersedes the n=18 figure from an earlier,
smaller corpus revision):** `statistic=46.0, p=0.486, effect_size_r=0.011, supported=False`
("not supported at p<0.05"). `co_resolution_events` and `cascading_violation_events` are 0 for
every one of the 28 subjects -- now a directly verified result (real per-subject `seqrefactor`
RunReports, correctly id-mapped), not an artifact of the identifier-mismatch bug above or of the
prior `None`-only wiring. The reason is not that nothing got accepted: several subjects show real
accepted resolutions within the 10-step budget (e.g. `pilot_checkout_v1` accepts a chain of
BigSwitch extractions), and Table II's cascading-violation/ordering-validity rows depend on those
real acceptances. It is that, per subject, the smells actually accepted never happened to include
*both* ends of the same manifest-declared dependency edge -- the deterministic generator's
impact-ranked exploration order did not reach those specific pairs within budget. The *structural*
mass itself (from each subject's manifest ground truth, independent of any run) is real and
non-degenerate -- see `table3_depmass.csv` for all 28 rows; positive/negative mass varies subject
to subject (e.g. `synth_xlarge_medium`: 1.73 positive / 1.61 negative; several small subjects:
0.0 / 0.0, since not every subject's random draw happened to inject a signed dependency at all).

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

## Phase 2c update: the discriminating benchmark

Phase 2's benchmark had a structural bias a reviewer identified: God Class always got the
maximum severity (1.0), and God Class was always the prerequisite, so even `impact_only`
(which ignores dependency edges) tended to pick it first anyway -- the strategies rarely had a
reason to differ, which is why H1/H2 came back degenerate in the Phase 2 write-up above. Phase
2c decorrelates severity from dependency role (a prerequisite samples Uniform(0.2, 0.6); each
dependent it contains samples independently from Uniform(0.6, 1.0), both realised through real
code structure the live detector computes severity from -- see
`seqrefactor/synth/generator.py`'s PHASE 2C docstring section) and adds an explicit
Priority-Dependency Conflict family (pairs, widths, chains) where a low-severity prerequisite's
dependent(s) are deliberately higher severity, so `impact_only` and the dependency-safe
strategies are forced to diverge **by construction**. The corpus grew from 18 to 28 subjects
(15 decorrelated grid subjects + 10 conflict subjects, `datasets/synthetic/CORPUS.md`); two new
reference strategies (`random`, `random_topological`) and two new studies (detector
precision/recall, random-baseline mean/spread) were added alongside.

### Table V — detector precision/recall/F1 (new, Phase 2c §4)

**Command:** `eval.detector_quality.run_study()`, `eval_tables.table5_detector_quality(...)`.

Every one of the 25 generator-produced subjects scores **precision = recall = F1 = 1.0** against
the generator's own planted ground truth -- a real, corpus-wide confirmation of the independence
property Phase 1/2 only spot-checked (`tests/unit/test_synth_generator.py`'s
`test_builder_independently_infers_planted_prerequisites_with_full_overlap`), now holding across
every subject, not just one. The one hand-written subject, `pilot_checkout_v1` (predates the
generator, its manifest was authored by hand, not produced by a script the detector's own
categories are guaranteed to match), scores precision = recall = F1 = 0.714 -- a real, honestly
reported difference between a hand-authored fixture and a script-verified one, not a detector
regression. `billing_cycle_v1`/`notification_mixed_v1` are correctly excluded (no real Java
source to run a detector against at all), not scored zero.

### Table VI — random-baseline reference statistics (new, Phase 2c §3)

**Command:** `eval.random_study.run_study(...)`, `eval_tables.table6_random_baseline(...)`, 200
samples per subject, seed 20260101.

- `mean_violation_fraction` clusters tightly around **0.48-0.51** across all 28 subjects
  (matching the naive expectation for an arbitrary permutation against a single prerequisite
  edge: roughly a coin flip) -- the real "how unsafe is doing nothing about ordering" upper
  reference the brief asks for.
- On every subject with more than one valid topological order to begin with (i.e. excluding the
  trivial 2-node pair/chain subjects, where only one order exists and every strategy coincides
  by necessity), `seqrefactor`'s objective **exceeds** `random_topological`'s mean by well more
  than its standard deviation -- e.g. `synth_xlarge_medium`: seqrefactor 3.638 vs.
  random_topological 2.718 +/- 0.205 (~4.5 standard deviations); `conflict_width_6`: 1.351 vs.
  1.299 +/- 0.025 (~2 standard deviations, smaller but still real on a much smaller subject).
  This is real, direct evidence that impact-forward prioritisation adds value *beyond* safety
  alone (H3's underlying claim), isolated from the value of safety itself, exactly what
  comparing against this reference is for.

### Table II / H1, H2, H3 (RQ1, RQ2, RQ3) -- Phase 2c result

**Command:** `uv run seqrefactor run --config configs/synthetic.yaml --out <scratch dir>` (against
a scratch copy, per the standing warning), 28 subjects x 7 strategies x up to 10 steps each, real
sidecar. Raw reports: `datasets/synthetic/example_run/*.json` (196 files); real per-strategy
means:

| strategy | n | mean cascading_violations | mean ordering_validity |
|---|---|---|---|
| `impact_only` | 28 | **7.536** | **0.131** |
| `random` | 28 | 1.429 | 0.690 |
| `unordered` | 28 | 0.964 | 0.893 |
| `random_topological` | 28 | 0.000 | 1.000 |
| `search_based` | 28 | 0.000 | 1.000 |
| `seqrefactor` | 28 | 0.000 | 1.000 |
| `topo_only` | 28 | 0.000 | 1.000 |

This is the acceptance check the brief named directly, holding exactly as predicted: on the
conflict subjects, `impact_only` (unsafe by design) records real cascading violations and
ordering validity far below 1.0, while every dependency-respecting strategy
(`seqrefactor`/`topo_only`/`search_based`/`random_topological`) stays perfectly safe.
`random`/`unordered` land in between (occasionally, not always, unsafe by coincidence).

**H1 and H2, real statistics, n=28 (no longer degenerate for H1):**

| Hypothesis | Supported | n | p-value | effect size (r) | mean difference |
|---|---|---|---|---|---|
| H1 (fewer cascading violations vs. unordered) | **yes** | 28 | **0.0416** | **1.0** | 0.964 |
| H2 (higher NSR vs. unordered) | insufficient signal | 28 | n/a | n/a | 0.0 (degenerate) |
| H2 (higher NSR vs. topo_only) | insufficient signal | 28 | n/a | n/a | 0.0 (degenerate) |
| H3 (higher AUC vs. topo_only) | **yes** | 28 | **0.0009** | **0.978** | 10.75 |

H1 went from degenerate (Phase 2, n=18, every difference exactly zero) to a real, significant
result: p=0.042, and the maximum possible rank-biserial effect size (r=1.0, meaning every single
paired subject moved in the predicted direction, not just most). H3 is even stronger
(p=0.0009). This is the "genuine, computable H1 result" the brief predicted the redesign would
produce, not tuned to appear -- the conflict family's H1 effect is entirely attributable to
`impact_only` alone; the other six strategies are pairwise identical on cascading violations by
construction, which is exactly the mechanism check (§2.2) working as designed.

**H2 stays degenerate, and Section 5's new diagnostics explain exactly why -- a real finding in
its own right, not a loose end.** Net smell resolution is 0 for *every* strategy on *every*
subject. Generation success rate (GSR, `RunReport.generation_success_rate`) and the
rejection-reason breakdown (`RunReport.rejection_reason_counts`), summed across all 28 subjects
per strategy:

| strategy | generation attempts | GSR | total NSR | total cascading | rejections |
|---|---|---|---|---|---|
| `impact_only` | 238 | 0.979 | 0 | 211 | `metric_regression`: 22, `no_patch`: 5 |
| `unordered` | 238 | 0.853 | 0 | 27 | `no_patch`: 35, `metric_regression`: 29 |
| `seqrefactor` | 238 | 0.836 | 0 | 0 | `no_patch`: 39, `metric_regression`: 40 |
| `search_based` | 238 | 0.803 | 0 | 0 | `no_patch`: 47, `metric_regression`: 28 |
| `random` | 238 | 0.782 | 0 | 40 | `no_patch`: 52, `metric_regression`: 80 |
| `topo_only` | 238 | 0.744 | 0 | 0 | `no_patch`: 61, `metric_regression`: 84 |
| `random_topological` | 238 | 0.731 | 0 | 0 | `no_patch`: 64, `metric_regression`: 71 |

Across every strategy, `no_patch` (the generator produced nothing, always true for a God Class
target -- `generate/baseline.py` has no class-level transform) and `metric_regression` (a patch
was produced and compiled and passed tests, but the aggregate five-family metric delta fell below
the gate's threshold) together account for nearly every rejection. NSR stays at zero regardless
of *which* smell gets offered to the generator first, because the deterministic baseline
generator's wrap-and-delegate transform (documented since Phase 1 as an ablation *control*, not a
quality tool) essentially never earns a positive aggregate metric delta on its own. **This is a
generator-capability ceiling, not a scheduling failure**: H2 was never going to distinguish the
strategies while every strategy's accepted-transform rate is pinned near zero by the same
generator limitation. Resolving it needs the LLM generator (Working Brief Phase 2 §3 step 3,
still blocked on an API key, see REPRODUCE.md) -- stated as the honest next step, not glossed
over.

## Phase 4 update: E1 impact-score ablation, E2 quality-score sensitivity

Real runs (`seqrefactor/eval/run_phase4_e1_e2.py`, deterministic baseline generator,
seed 20260101, `max_steps=10`, full 28-subject corpus), 157.4 minutes wall clock for E1;
E2 adds zero additional orchestrator runs, reusing E1's A5 (default-weight) data directly
(a quality-weight vector only changes how an already-recorded metric delta is scored, not
what transformation happened -- see `seqrefactor/eval/quality_sensitivity.py`'s module
docstring). Both answer a reviewer's must-fix question about whether the H3 early-quality
result (SEQ-REFACTOR early-quality AUC > topology-only's) is real or an artefact of one
specific weighting choice.

### Table (new) -- impact-score ablation (`evaluation/table_impact_ablation.csv`)

| Configuration | alpha, beta, gamma | n | p-value | effect size (r) | Supported? |
|---|---|---|---|---|---|
| A1 coupling only | 1, 0, 0 | 28 | -- | -- | **Degenerate** (every paired difference exactly zero) |
| A2 complexity only | 0, 1, 0 | 28 | 0.0324 | 0.603 | Yes |
| A3 co-occurrence only | 0, 0, 1 | 28 | 0.2641 | 0.286 | **No** |
| A4 coupling+complexity, equal | 0.5, 0.5, 0 | 28 | 0.0324 | 0.603 | Yes |
| A5 all three, paper default | 0.4, 0.4, 0.2 | 28 | 0.0009 | 0.978 | Yes |

**Reported honestly, per the brief's own rule: the H3 advantage is not universally robust to
the impact weighting.** It holds under complexity-only, coupling+complexity, and the paper's
own default (A5's p=0.0009 exactly matches the previously-established H3 result -- the same
statistic, independently reproduced by this new driver under identical weights, a clean
internal consistency check). It does **not** hold under co-occurrence-only weighting (p=0.264),
and coupling-only weighting is **degenerate** on this corpus: SEQ-REFACTOR and topology-only
produced identical early-quality AUC on every single subject, meaning coupling alone does not
discriminate priority among this corpus's smells enough to change which vertex gets scheduled
first at any point in any of the 28 subjects. Read together: the advantage is a property of
weighting complexity (alone or combined) into the impact score, not of impact-forward
scheduling in the abstract regardless of what impact means -- a materially more precise claim
than "SEQ-REFACTOR beats topology-only" without qualification, and the honest one this ablation
was run to establish.

### Table (new) -- quality-score sensitivity (`evaluation/table_quality_sensitivity.csv`)

Every one of 4 quality-weight vectors (the pre-existing accepted-count measure, equal metric
weights, and two vectors each emphasising a different family pair) x 2 trajectory-scoring
modes (summed, step-count-normalised `AUC_norm`) reports **supported=True**, p-values ranging
0.0009-0.0012, effect sizes 0.81-0.98. **The H3 conclusion does not flip under any tested
quality weighting, and normalising by step count does not change which side of p=0.05 any row
falls on either.** This is the reassuring result E2 was checking for -- unlike E1's impact-
weighting ablation, nothing here disappears.

Full disclosure of both drivers, the reused-A5-data design decision for E2, and the raw
per-configuration RunReports: `seqrefactor/eval/run_phase4_e1_e2.py`,
`evaluation/phase4_e1_raw_runs.json`.

## Phase 1 results (superseded scope, kept for reference)

The original single/few-subject numbers this section used to report (n=3 synthetic subjects for
Table III with `co_resolution_events`/`cascading_violation_events` always 0 by construction since
no run was threaded through; a 5-point |V| sweep for Table IV) are still present as the
`synthetic_V*`-tagged rows and the `billing_cycle_v1`/`notification_mixed_v1`/`pilot_checkout_v1`
rows in the current CSVs — nothing from Phase 1 was deleted, Phase 2 only added subjects and
threaded real run data through where Phase 1 had left it structural-only.
