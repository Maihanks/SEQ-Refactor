# evaluation/ — Tables III and IV, real committed results

Deliberately **not** named `results/`/`runs/` (both gitignored elsewhere in this repo as
regenerable output) — this directory holds specific, committed snapshots that back numbers
written into the paper, the same role `datasets/opensource/json_java_v1/example_run/` plays for
Table II. Regenerating either table (commands below) will very likely reproduce these exact
values (both studies are seeded and deterministic), but if you do, treat the new output as
superseding this snapshot rather than assuming it must match to the last digit — wall-clock
timings in particular are hardware-dependent.

## Table III — dependency-mass study (RQ5, H4)

**Command:**

```python
from pathlib import Path
from seqrefactor.datasets import graph_from_manifest, list_subjects, load_manifest
from seqrefactor.eval import tables as eval_tables
from seqrefactor.eval.depmass import run_study

entries = [(s, graph_from_manifest(load_manifest(s)), None) for s in list_subjects()]
masses, h4 = run_study(entries)
eval_tables.table3_depmass(masses, out_dir=Path("evaluation"))
```

**Result:**

| subject | positive_mass | negative_mass | mass_ratio | co_resolution_events | cascading_violation_events |
|---|---|---|---|---|---|
| billing_cycle_v1 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| notification_mixed_v1 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| pilot_checkout_v1 | 0.6 | 0.25 | 0.4167 | 0 | 0 |

**H4** (avoided-negative-mass vs. forgone-positive-mass, paired Wilcoxon): `n=3`,
`supported=None`, note: *"only 3 subject(s) available (minimum 5 to run the paired test at all);
... this is a data-coverage gap, not a negative result."* No p-value, no effect size — none
computed, none reported, matching the standing constraint against fabricated statistics.

**What this number is, precisely, and what it is not:**

- `billing_cycle_v1` and `notification_mixed_v1` show zero mass because neither manifest declares
  any `positive_dependencies`/`negative_dependencies` (only `pilot_checkout_v1`'s does — see
  `datasets/synthetic/pilot_checkout_v1/manifest.yaml`). This is not a detection failure; it is
  that only one of the three synthetic subjects currently has injected signed-edge ground truth
  (Working Brief §7's ask; extending the other two manifests is future work, see REPO_MAP.md).
- `co_resolution_events`/`cascading_violation_events` are both 0 for every subject because `run`
  was passed as `None` above — no executed `RunReport` was supplied, so only the *structural*
  mass (from the manifest's declared ground truth) is computed, per
  `eval/depmass.dependency_mass_for_subject`'s own documented contract. Realised events need an
  actual pipeline run threaded through; getting a non-trivial realised count would need
  `pilot_checkout_v1`'s injected `s5->s6` (positive) / `s3->s4` (negative) pair to actually be
  visited by an ablation run within its step budget, which was not attempted here. Reported as
  zero because that is what was actually measured, not because a real value would necessarily be
  zero -- this is exactly the "structural mass, not realised outcomes" scope the summary note
  below states.
- HONESTY NOTE (already stated on `model.DependencyMass` and `graph/rules.py`, repeated here
  because it directly bears on how to read this table): the 0.6/0.25 probabilities themselves are
  illustrative catalogue defaults seeded by directional plausibility, not mined from version
  history. This table measures a *modelled* distribution, not an *observed* one.

## Table IV — complexity-scaling study (RQ6, H5)

**Command:**

```python
from pathlib import Path
from seqrefactor.eval import tables as eval_tables
from seqrefactor.eval.complexity import run_scaling_study

records = run_scaling_study(
    module_sizes=[10, 25, 50, 100, 200], max_steps_per_size=10, repeats=7, seed=20260101
)
eval_tables.table4_efficiency(records, out_dir=Path("evaluation"))
```

**Result** (88 rows total in `table4_efficiency.csv`; aggregated here as mean `edge_touches` per
module size |V|, across every step and both maintenance strategies at that size):

| \|V\| | from-scratch mean edge_touches | incremental mean edge_touches | ratio |
|---|---|---|---|
| 10 | 11.5 | 1.5 | 7.7x |
| 25 | 121.6 | 1.4 | 86.9x |
| 50 | 947.0 | 2.6 | 364.2x |
| 100 | 6216.0 | 3.0 | 2072.0x |
| 200 | 31816.0 | 3.0 | 10605.3x |

This is the empirical scaling signature the paper's H5 predicts: from-scratch edge touches grow
roughly with |V|^2 (O(|V|^2) pairwise rebuild), while incremental edge touches stay roughly flat
(scoped to the disturbed region, independent of module size) — the ratio between them grows from
under 8x at |V|=10 to over 10,000x at |V|=200. Every row's bit-for-bit equivalence to a
from-scratch rebuild is what `tests/property/test_incremental_equivalence.py` proves (by
construction, not just by this measurement) — see `graph/incremental.py`'s design-note docstring
for why the efficiency claim is scoped to detection + graph-rebuild cost specifically, not the
ordering step itself.

**Scope, stated plainly**: this is a synthetic, seeded scaling study (`eval/complexity.py`), not a
measurement against the checked-in real subjects — `pilot_checkout_v1` (7 smells) and
`json_java_v1` (126 smells) are both far smaller than the |V| range that makes the asymptotic
trend visible, which is exactly why this module exists as a separate, deliberately-scaled study
rather than reusing the real subjects. Wall-clock timings in the raw CSV are median-of-7-repeats
per the module's own docstring, but are still hardware-dependent — the ratio/trend is the durable
claim, not any single absolute microsecond figure.
