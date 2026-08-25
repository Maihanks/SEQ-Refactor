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

```bash
uv run python -c "
from pathlib import Path
from seqrefactor.eval import tables as eval_tables
from seqrefactor.eval.complexity import run_scaling_study

records = run_scaling_study(module_sizes=[10, 25, 50, 100, 200], max_steps_per_size=10, repeats=7, seed=20260101)
eval_tables.table4_efficiency(records, out_dir=Path('evaluation'))
"
```

`tests/property/test_incremental_equivalence.py` is the bit-for-bit equivalence proof every
number in this table depends on (H5) -- run it (`uv run pytest tests/property -q`) alongside any
regeneration, not as a one-time check.

Then regenerate Fig. 5 and its labelled step-0/session-mean summary from the table you just wrote
(Phase 3c G1/G3):

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
