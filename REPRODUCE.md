# REPRODUCE.md

How to regenerate every number in this repository's `results`/`evaluation`/`datasets` output
from a clean checkout, in order. Written per Working Brief, Phase 2, Section 8's Definition of
Done ("A REPRODUCE.md explains how to run everything from a clean checkout, including tool
versions").

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

## 6. Everything in one command

```bash
make results   # = uv run seqrefactor results --config configs/ablation.yaml --out results
```

Table II only (the open-source subject's ablation); Tables III/IV are separate commands above
because they operate on the synthetic corpus, not `configs/ablation.yaml`'s subject. `results/`
is gitignored (regenerable); committed snapshots of specific runs live under
`datasets/opensource/json_java_v1/example_run/` and `evaluation/` instead, each with its own
`README.md`/`PROVENANCE.md` explaining exactly what was run and when.

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
