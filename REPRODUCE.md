# REPRODUCE.md

How to regenerate every number in this repository's `results`/`evaluation`/`datasets` output
from a clean checkout, in order. Written per Working Brief, Phase 2, Section 8's Definition of
Done ("A REPRODUCE.md explains how to run everything from a clean checkout, including tool
versions").

## Table and figure numbering: repo vs. paper (Phase 3c G4)

The `tableN_*` filenames under `evaluation/` are this repo's own internal sequence -- assigned in
the order each table was added during development -- and do **not** track the paper's table
numbers one-to-one. Cross-reference, established directly from the paper text
(`draft docs/SEQ_REFACTOR_paper.docx`):

| Repo artefact | Repo label | Paper reference | Confidence |
| --- | --- | --- | --- |
| `evaluation/table2_ablation.*` | "Table II" | **Table IV** ("the four-arm ablation on the open-source subject json_java_v1") | explicit in paper text |
| `evaluation/table3_depmass.*` | "Table III" | **Table VI** ("dependency-mass comparison of RQ5/H4") | explicit in paper text |
| `evaluation/table4_efficiency.*` | "Table IV" | **Table VII** ("the efficiency study of RQ6/H5") | explicit in paper text |
| `evaluation/table6_random_baseline.*` | "Table VI" | **Table V** (aggregates the mean of each measure across the 28 subjects; describes sampling uniformly among valid linear extensions) | inferred from context, not an explicit "(Table V)" citation next to this data -- verify before citing |
| `seqrefactor/graph/rules.py` `PRECEDENCE_RULES` | (no repo table number; a Python literal, not an emitted table) | **Table III** ("illustrative subset" of precedence rules) | explicit in paper text |
| paper's symbol glossary | no repo equivalent | **Table I** | explicit in paper text; paper-only content |
| paper's comparison against prior approaches | no repo equivalent | **Table II** | explicit in paper text; qualitative, paper-only content |
| `evaluation/table5_detector_quality.*` | "Table V" | not currently cited by paper table number found in this pass | internal detector QA, not yet matched to a paper table |
| `evaluation/fig_scaling.png`/`.pdf` (`seqrefactor/eval/plot_scaling.py`) | -- | referred to as **Fig. 5** by the Phase 3c working brief | **not found in the committed paper**: the paper currently has only Fig. 1-4, and no figure captioned as a scaling plot. Either a newer paper draft than what's committed here already has it, or it is still to be added -- verify against the author's current working copy before citing "Fig. 5" in a submission. |
| the O(k\|V\|^2) -> O(kd) session bound (see `seqrefactor/eval/complexity.py`, `seqrefactor/graph/incremental.py`) | -- | referred to as **Proposition 1** by the Phase 3c working brief | **not found as a formally labelled proposition in the committed paper**: Section VI-A states the same argument in prose ("under the bounded-locality assumptions of Section VI-A the per-step re-analysis is proportional to the disturbed subgraph..."), not as a numbered "Proposition 1". Same caveat as Fig. 5 above. |

The last two rows are a **documentation-currency finding**, not a data mismatch: every measured
number this task touches (the CSV data, the 38,416/31,816 step-0/session-mean pair, the 3.05x
median / 4.10x mean wall-clock ratio, the ~2402-to-~1.65 mean edge-touches drop) was independently
recomputed from the committed `evaluation/table4_efficiency.csv` during this synchronisation pass
and matches the working brief's cited values exactly. What doesn't yet exist in the committed
`.docx` is the "Fig. 5" and "Proposition 1" *labels* themselves -- the repository-side artefacts
those labels would point to (the figure, the explicit bound statement) are now built and
verified; wiring the paper's own text to them is a paper edit, not a repo one.

## Tool versions this was built and verified against

- Python 3.12.3, managed via [uv](https://docs.astral.sh/uv/) 0.11.20
- JDK 21 (a **full** JDK, not a JRE: `javac` must be on `PATH` or `JAVA_HOME`). This
  environment's system Java was JRE-only; a portable
  [Eclipse Temurin 21](https://adoptium.net/) JDK was downloaded to a scratch directory (no root
  needed) and pointed at via `JAVA_HOME` instead. Any JDK 21+ works; if your system one is a
  full JDK, you don't need this step.
- Gradle (via the checked-in `jvm-sidecar/gradlew` wrapper, downloads Gradle 8.10.2 itself)

## 1. Python environment

```bash
uv sync --group dev
```

## 2. The JVM sidecar (needed for anything that compiles/tests/measures real Java: the main
## ablation, the generator's compile/test acceptance check, and Table VI's real-corpus half)

```bash
cd jvm-sidecar
./gradlew build   # gradlew.bat on Windows; needs a full JDK on PATH, see above
cd ..
```

Verify: `uv run pytest -q` should show **0 skips** (sidecar-dependent tests skip cleanly, with a
clear reason, if this step wasn't done or failed).

## 3. Regenerate the synthetic corpus (optional -- it's already committed under
## `datasets/synthetic/`, but this reproduces it from scratch, byte-for-byte, from the master
## seed alone)

```bash
uv run python -c "
from seqrefactor.synth.build_corpus import build_corpus, write_corpus_md
build_corpus()
write_corpus_md()
"
```

See `datasets/synthetic/CORPUS.md` for what this produces (15 generated subjects, their spec
parameters, and why) and `seqrefactor/synth/generator.py`'s module docstring for the generation
method itself (what each smell category's real Java pattern is, why Feature Envy and other
catalogue-only categories are out of scope, why cycle subjects are manifest-declared rather than
builder-discoverable).

## 4. Run the full ablation matrix (five strategies, the whole corpus)

**Never point `subjects_glob` at `datasets/synthetic/` or `datasets/opensource/` directly** -- the
orchestrator mutates its target module in place. Copy first:

```bash
cp -r datasets/synthetic /tmp/scratch_synthetic
```

Edit a copy of `configs/synthetic.yaml` (or use `sed`) so `subjects_glob` points at
`/tmp/scratch_synthetic/*/` instead of `datasets/synthetic/*/`, then:

```bash
uv run seqrefactor run --config <edited-config> --out /tmp/scratch_runs
```

This is the expensive step: 18 subjects (15 generated + 3 hand-written, 2 of the latter having no
real Java source and returning instantly) x 5 strategies x up to 10 steps each, each step a real
sidecar compile+test(+metrics) cycle. Budget on the order of 30 minutes; see
`configs/synthetic.yaml`'s own comment for the per-step cost measurement this estimate is based
on. `uv run seqrefactor results --config <edited-config> --out /tmp/scratch_results` runs the same
matrix and additionally regenerates Tables II-IV and `SUMMARY.md` in one command (Phase 1's
`make results`, extended by Phase 2's search_based strategy and larger corpus).

## 5. Tables III/IV (dependency-mass, complexity-scaling) against the corpus

**The session-level bound Table IV / Fig. 5 measure (Phase 3c G2, "Proposition 1" in the working
brief's terms -- see the numbering note above):** naive rebuilding of the smell-dependency graph
costs O(k\|V\|^2) edge derivations over a k-step session (every step re-derives all pairs of the
surviving smells); incremental maintenance (`graph/incremental.apply_step`) costs O(kd), where d
is the size of the disturbed region one accepted transformation actually touches, independent of
\|V\| for a local refactoring. The worst case (a transformation disturbing the whole module)
recovers the O(k\|V\|^2) cost. This is a bound on operation counts (vertex/edge touches), stated
and measured separately from wall-clock time, which is hardware-dependent -- see
`seqrefactor/eval/complexity.py`'s module docstring for the full statement.

```bash
uv run python -c "
from pathlib import Path
from seqrefactor.datasets import graph_from_manifest, list_subjects, load_manifest
from seqrefactor.eval import tables as eval_tables
from seqrefactor.eval.depmass import run_study

entries = [(s, graph_from_manifest(load_manifest(s)), None) for s in list_subjects()]
masses, h4 = run_study(entries)
eval_tables.table3_depmass(masses, out_dir=Path('evaluation'))
print(h4)
"
```

To thread *realised* co-resolution/cascading events (rather than structural mass only) into this
table, pass the actual `RunReport`s from step 4 instead of `None` for each entry -- see
`eval/depmass.dependency_mass_for_subject`'s docstring.

`evaluation/table4_efficiency.csv` (334 rows) is two measurements concatenated, distinguished by
the `subject` column (`evaluation/README.md`'s "Table IV" section documents both in full):

**1. The synthetic |V| sweep (88 rows, `subject` = `synthetic_V<n>`)** -- exactly reproducible from
current code, byte-for-byte on every deterministic counter column (verified during Phase 3c: a
fresh run of the command below reproduces all 88 rows' `vertex_touches`/`edge_touches` exactly).
**This is the half the paper's cited numbers come from** -- the step-0 (38,416) and session-mean
(31,816) values at V=200, and Fig. 5 itself:

```bash
uv run python -c "
from pathlib import Path
from seqrefactor.eval import tables as eval_tables
from seqrefactor.eval.complexity import run_scaling_study

records = run_scaling_study(module_sizes=[10, 25, 50, 100, 200], max_steps_per_size=10, repeats=7, seed=20260101)
eval_tables.table4_efficiency(records, out_dir=Path('evaluation'))
"
```

**2. The real corpus cross-validation (246 rows, real subject names, `eval.complexity.run_corpus_study`)**
-- **a Phase 2 snapshot, not exactly reproducible by a fresh call today**, verified during Phase 3c:

```bash
uv run python -c "
from seqrefactor.eval.complexity import run_corpus_study
records = run_corpus_study(max_steps_per_subject=10, repeats=7)
print(len(records))   # 266 today, not 246 -- see below
"
```

Running this today produces 266 rows, not 246, and the deterministic counters that do overlap by
key differ on 267 of them. This is not a bug in either the code or the committed CSV -- the
corpus and the synthetic generator that builds it changed *after* this table's corpus rows were
generated: Phase 2c (see `evaluation/README.md`'s "Phase 2c update" section) grew the corpus from
18 to 28 subjects (adding the `conflict_*` family, some of which now contribute the extra rows)
and decorrelated severity from dependency role in `seqrefactor/synth/generator.py`, which changes
which vertex gets resolved at each step and therefore which edges get re-derived. The committed
246 rows are a legitimate, real measurement -- just one taken against an earlier state of the
corpus, kept as a committed snapshot (per `evaluation/README.md`'s own framing of this directory)
rather than silently replaced by a newer run whose numbers would differ for reasons that have
nothing to do with the incremental-vs-from-scratch question this table exists to answer. **Do not
overwrite `evaluation/table4_efficiency.csv`'s corpus rows with a fresh `run_corpus_study()` call**
without first deciding, deliberately, whether you want this table to mean "Phase 2 corpus,
comparable across the project's history" or "current corpus, current numbers" -- and updating
`evaluation/README.md`'s narrative to match, since it currently describes and tabulates the Phase
2 values specifically.

`tests/property/test_incremental_equivalence.py` is the bit-for-bit equivalence proof every
number in this table depends on (H5) -- run it (`uv run pytest tests/property -q`) alongside any
regeneration, not as a one-time check. It passes against both the Phase 2 snapshot's construction
and today's corpus, since the equivalence is proven by construction (see
`graph/incremental.py`'s docstring), not tied to a specific corpus state.

Then regenerate Fig. 5 and its labelled step-0/session-mean summary from the table you just wrote
(Phase 3c G1/G3) -- this reads only the synthetic-sweep-derived columns' aggregate behaviour by
module size, so it is unaffected by the corpus-snapshot question above:

```bash
make scaling   # = uv run python -m seqrefactor.eval.plot_scaling
```

This reads `evaluation/table4_efficiency.csv` alone -- it does not re-run the scaling study itself
(that's the `run_scaling_study` command above) -- and writes `evaluation/fig_scaling.png`/`.pdf`
and `evaluation/scaling_summary.md` deterministically from whatever is currently in that CSV.
Re-run the `run_scaling_study` command first if you want the figure to reflect a fresh
regeneration rather than the currently-committed table.

## 6. Everything in one command

```bash
make results   # = uv run seqrefactor results --config configs/ablation.yaml --out results
```

Table II only (the open-source subject's ablation); Tables III/IV are separate commands above
because they operate on the synthetic corpus, not `configs/ablation.yaml`'s subject. `results/`
is gitignored (regenerable); committed snapshots of specific runs live under
`datasets/opensource/json_java_v1/example_run/` and `evaluation/` instead, each with its own
`README.md`/`PROVENANCE.md` explaining exactly what was run and when.

`make scaling` (Phase 3c G6) is the equivalent one-command step for Fig. 5 -- see step 5 above.

## 7. Verification: headline numbers re-derived from committed data (Phase 3c)

Before adding anything in this Phase 3c pass, every headline number the working brief cited was
independently recomputed from the already-committed CSVs (never from the brief's own text) and
compared. All matched; no drift found. Re-run these to re-verify at any time -- they only read
committed files, nothing here re-runs an experiment:

```bash
# H1, H3, H4: read directly, no computation needed
cat evaluation/SUMMARY.md
# H1_fewer_cascading_violations_vs_unordered: p=0.04163 (n=28)  -> brief cites p=0.042
# H3_higher_auc_vs_topo_only:                 p=0.0009208 (n=28) -> brief cites p=0.0009
# H4_dependency_mass:                          p=0.4861, not supported -> brief cites p=0.486

# H4's realised co-resolution/cascading events are 0 for every subject:
uv run python -c "
import csv
rows = list(csv.DictReader(open('evaluation/table3_depmass.csv')))
events = [(r['co_resolution_events'], r['cascading_violation_events']) for r in rows]
print('all zero:', all(a == '0' and b == '0' for a, b in events), '/ n =', len(rows))
"

# H5 wall-clock ratio (median/mean, across every paired from-scratch/incremental
# step-level observation) and the mean edge-touches drop:
uv run python -c "
import csv, statistics
rows = list(csv.DictReader(open('evaluation/table4_efficiency.csv')))
by = {}
for r in rows:
    by.setdefault((r['subject'], int(r['step_index'])), {})[r['strategy']] = r
wall = [float(d['from_scratch']['wall_clock_seconds']) / float(d['incremental']['wall_clock_seconds'])
        for d in by.values() if 'from_scratch' in d and 'incremental' in d
        and float(d['incremental']['wall_clock_seconds']) > 0]
fs_edges = [float(r['edge_touches']) for r in rows if r['strategy'] == 'from_scratch']
inc_edges = [float(r['edge_touches']) for r in rows if r['strategy'] == 'incremental']
print('n paired observations:', len(wall))
print('wall-clock median:', round(statistics.median(wall), 2), '-> brief cites 3.05x')
print('wall-clock mean:', round(statistics.mean(wall), 2), '-> brief cites 4.10x')
print('mean edge_touches from_scratch:', round(statistics.mean(fs_edges), 2), '-> brief cites ~2402')
print('mean edge_touches incremental:', round(statistics.mean(inc_edges), 2), '-> brief cites ~1.6')
"

# Table VII / Fig. 5 headline pair, from the synthetic-sweep half only (Section 5 above):
uv run python -m seqrefactor.eval.plot_scaling
# edge_derivations_step0_V200 = 38,416.00      -> brief cites 38,416
# edge_derivations_session_mean_V200 = 31,816.00 -> brief cites 31,816
```

**Result: zero drift on every one of these.** The one caveat, stated in full in section 5 above:
the wall-clock/edge-touches aggregates here are computed across all 334 rows, including the 246
Phase-2-snapshot corpus rows -- if that corpus half is ever regenerated against the current (Phase
2c) corpus, these two aggregate figures (not the step-0/session-mean pair, which is
synthetic-sweep-only and already re-verified exactly) would need re-checking against whatever the
paper cites at that time.

## What needs an API key (not available in this environment)

The LLM generator (`generate/llm.py`) needs `OPENAI_API_KEY`. No `.env` file exists in this
checkout, so every run referenced above uses the deterministic baseline generator only. Section 3
of the Phase 2 brief's LLM-generator run (a stronger, non-baseline-limited version of Table II) is
not done here for that reason -- it's the one Definition-of-Done item this REPRODUCE.md cannot
itself close; supply a key and follow this same procedure with `generators: ["llm"]` (or
`--generator llm` where a CLI flag exists) to do it.

## Known cost/scope decisions (see PHASE2_PLAN.md and CORPUS.md for the reasoning)

- Generated subjects are smaller (5-16 real classes) than the brief's suggested 8-25 range, and
  `max_steps` is bounded (10, not each subject's full smell count), both to keep a full corpus
  run inside a single reasonable session. Raise either for a larger, slower run.
- The generator plants only the four smell categories the native detector
  (`detect/native.py`) actually supports; Feature Envy and other catalogue-only categories are
  out of scope (see the generator's own SCOPE NOTE).
- `search_based` (Working Brief Phase 2 §4) is a real, working genetic algorithm over this
  repository's own optimisation objective (paper Eq. 2), not a verified reproduction of Ouni et
  al. [29] or Liu et al. [30]'s exact published algorithms -- see `order/search_based.py`'s
  HONESTY NOTE for why that distinction matters and cannot be closed in this environment.
