# E4 pilot: controlled LLM run (Working Brief Phase 4, Task E4)

**This is a reduced-scope pilot, not the full brief-specified matrix** (8 strategies x
28 subjects x N=3). Scope chosen explicitly by the repository owner given the real API
cost/time of the full matrix, pending real numbers from this smaller run first. See
`seqrefactor/eval/run_phase4_e4_pilot.py` for the exact driver.

## Configuration (full disclosure, brief's own requirement)

- **Model**: `gpt-5`, via the OpenAI Chat Completions API (`seqrefactor/generate/llm.py`).
- **Temperature**: requested at `0.0`; `gpt-5` rejects this (400 `Unsupported value` error)
  and only supports its default (1.0) -- the adapter now retries without the parameter
  when a model refuses it (see the `generate/llm.py` diff in the commit this pilot
  shipped with). So this pilot ran at the model's default temperature, not `0.0`.
- **Seed**: `seed` is still passed to the API on every call (OpenAI's best-effort
  determinism hint); each of the 3 repetitions uses a distinct base seed
  (`20260101`, `20261101`, `20262101`) specifically so repetitions are genuine
  independent draws rather than replays of the same cache entry (`generate/llm.py`
  caches by a hash that includes the seed).
- **Strategies**: `seqrefactor`, `unordered`, `topo_only` -- the exact three strategies
  `report.hypothesis_tests` pairs for H1/H3, chosen so this pilot could compute real
  H1/H3-under-LLM numbers, not just generation-success-rate.
- **Subjects**: `pilot_checkout_v1`, `synth_small_medium`, `synth_medium_medium`,
  `conflict_pair_a` -- 4 representative subjects (the paper's own pilot subject, two
  synthetic-generator tiers, one conflict-family subject), not the full 28.
- **Repetitions**: N=3 (the brief's stated minimum).
- **max_steps**: 5 (reduced from the corpus default of 10, to bound pilot cost/time).
- **Retrieval, tool configuration**: unchanged from the rest of this repository --
  `seqrefactor/retrieve/retriever.py` (TF-IDF vector + in-memory structural retrieval,
  no external vector store), no additional tools beyond the generator itself.
- **Retry policy / timeout**: whatever the `openai` Python SDK's own defaults are;
  this pilot did not configure custom retry/timeout behaviour.
- Every response is cached to disk (`runs/llm_cache/`, gitignored -- regenerable, not
  itself a claim of committed evidence) keyed by a hash of (target, context, seed,
  model), and replayed rather than re-queried on any future reproduction run with the
  same inputs (NFR-2).

## What actually happened (36 runs, 82.1 minutes wall clock)

- **Generation success rate = 1.00 on every single one of the 36 runs** (up to 5 steps
  each). The deterministic baseline generator returns `no_patch` for class-level smells
  like GodClass (see `generate/baseline.py`'s own scope note); `gpt-5` did not hit this
  limitation once in this pilot. This is consistent with the brief's own expectation
  ("H2 ... now potentially testable since a capable model can resolve class-level
  smells") -- worth testing at full scale, not yet confirmed as a general result from
  4 subjects.
- **Real, non-degenerate variance across repetitions** at the same (subject, strategy):
  e.g. `pilot_checkout_v1`/`seqrefactor`'s net smell resolution was 2, 1, 1 across the
  three repetitions -- confirming the distinct-seed design actually captures LLM
  non-determinism rather than replaying identical cached output.
- **Cascading violations appeared under `unordered`, never under `seqrefactor` or
  `topo_only`**: `pilot_checkout_v1`/`unordered` cascaded 3 times in repetition 1 and 5
  times in repetition 2 (0 in repetition 0); every other (subject, strategy) cell
  across all three strategies and all three repetitions recorded 0. Under the
  deterministic baseline generator (see `evaluation/README.md`'s Phase 2c section),
  cascading violations are near-universally 0 regardless of strategy, because the
  baseline barely resolves anything (GSR much lower, per the same generation-success-
  rate diagnosis above). A capable generator that actually resolves class-level smells
  appears to be what makes the safety difference between dependency-aware and
  unordered scheduling *observable* at all -- directionally consistent with this
  project's central claim, but from one subject's two non-zero observations, not yet a
  general result.

## H1 / H3 under the LLM generator (n=12: 4 subjects x 3 repetitions, paired per
## (subject, repetition), not just per subject -- see the `repetition` field this
## pilot's analysis added to `RunReport`)

| Hypothesis | n | p-value | effect size (r) | mean difference | supported (p<0.05) |
|---|---|---|---|---|---|
| H1 (fewer cascading violations, seqrefactor < unordered) | 12 | 0.25 | 1.0 | 0.667 | **No** |
| H3 (higher early-quality AUC, seqrefactor > topo_only) | 12 | 0.241 | 0.273 | 1.167 | **No** |

**Neither is statistically significant at this pilot's scale.** Report this plainly,
per the brief's own rule ("report whatever the experiments produce"). Both point in
the expected direction (H1's effect size of 1.0 reflects that the only two non-zero
paired differences both favoured `seqrefactor`; H3's mean difference is positive), but
n=12 paired observations is a small sample for a noisy, real-generator signal, and
this pilot was never scoped to reach significance -- it was scoped to surface real
cost, timing, and mechanism before committing to the full 8x28x3 matrix, which it did.

## A real bug this pilot surfaced and fixed, not just data

`report.py`'s pairing logic (`_paired_values`, used by `hypothesis_tests`) keyed only
on `(subject, generator)`. With N repetitions sharing that same key, later repetitions
silently overwrote earlier ones in the pairing dict -- the *raw* RunReports were all
saved correctly (nothing here was lost), but the *aggregate statistic* computed from
them would have silently used only the last repetition. Fixed by adding a `repetition`
field to `RunReport` (default 0, so every pre-existing single-run RunReport is
unaffected) and keying pairing on `(subject, generator, repetition)` instead -- see
`tests/unit/test_report.py::test_repeated_runs_of_the_same_cell_are_independent_paired_observations`.
The 36 RunReports in this directory were generated before this fix existed and were
patched in place (`repetition` set from save order, 12 runs -- 4 subjects x 3
strategies -- per repetition) once it landed; `summary.json` here reflects the
corrected, patched data.

## Reproducing this pilot

```bash
cp -r datasets/synthetic/pilot_checkout_v1 datasets/synthetic/synth_small_medium \
      datasets/synthetic/synth_medium_medium datasets/synthetic/conflict_pair_a \
      /tmp/scratch_e4_pilot/
SEQREFACTOR_LLM_MODEL=gpt-5 uv run python -m seqrefactor.eval.run_phase4_e4_pilot \
  --scratch-corpus /tmp/scratch_e4_pilot --out-dir evaluation/llm_pilot
```

Needs `OPENAI_API_KEY` set (`.env`, gitignored, never committed). Real generation
happens only for prompts not already in `runs/llm_cache/`; a from-scratch reproduction
will make real (billed) API calls.
