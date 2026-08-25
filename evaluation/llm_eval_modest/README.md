# Modest LLM-generator confirmatory run

A real, API-backed LLM-generator evaluation (`seqrefactor.generate.llm`, `gpt-4.1-mini`,
`temperature=0`, `seed=20260101`), run once an `OPENAI_API_KEY` became available. Scope was kept
small deliberately (4 subjects, `strategies: ["seqrefactor"]`, `max_steps: 10`): `pilot_checkout_v1`,
`synth_small_low`, `synth_medium_cycle`, `synth_medium_high_signed`, chosen because each carries
explicit `positive_dependencies`/`negative_dependencies` ground truth (the structure RQ5/H4 needs).
Subjects were copied to a scratch directory before running (the orchestrator mutates its target
module in place; never point `subjects_glob` at `datasets/synthetic/` directly, see REPRODUCE.md).

Re-run with (after `export OPENAI_API_KEY=...` and building `jvm-sidecar`, see REPRODUCE.md):

```bash
cp -r datasets/synthetic/pilot_checkout_v1 datasets/synthetic/synth_small_low \
      datasets/synthetic/synth_medium_cycle datasets/synthetic/synth_medium_high_signed \
      /tmp/llm_eval_scratch/
uv run seqrefactor run --config evaluation/llm_eval_modest/config_used.yaml --out /tmp/llm_eval_out
```

(edit `config_used.yaml`'s `subjects_glob` to point at the scratch copy first)

## Result

All 4 subjects: `cascading_violations = 0`, `ordering_validity = 1.0` (the seqrefactor strategy
never executed a step whose prerequisites were unsatisfied, and never triggered a step-level
cascading-violation flag, exactly as under the deterministic baseline generator; see
`summary.json`).

`co_resolution_events` (the other half of H4, computed by
`eval.depmass.dependency_mass_for_subject` matching each subject's manifest-declared
`positive_dependencies` edges, e.g. `pilot_checkout_v1`'s `s5 -> s6`, against
`RunReport.steps[].smell`) also remained 0 for all 4 subjects under the real LLM generator, exactly
as under the baseline generator. Inspecting *why*: the manifest's ground-truth positive/negative
dependency edges are declared over hand-picked smell locations (e.g. `s5 = MessageChains at
orders.OrderService.notifyWarehouse`), but the live pipeline's own detector
(`seqrefactor/detect/native.py`, via `graph/builder.py`) independently derives its own
`SmellInstance` identifiers for whatever it actually finds in the (possibly LLM-edited) source at
each step. For `pilot_checkout_v1`, the accepted-smell set from this real run was
`MessageChains:orders.OrderService.priceOf`, `...calculateShipping`,
`...calculateRegionalSurcharge`, `...getShippingZoneCode` (real message chains the detector found)
rather than the manifest's declared `notifyWarehouse`/`notifyBilling` locations. The two
identifier spaces (manifest ground truth vs. live detector output) do not correspond, so
`dependency_mass_for_subject`'s realised-co-resolution check is structurally unable to fire for
*any* generator, deterministic or LLM, unless a subject's live detection output happens to
rediscover the exact manifest-declared locations verbatim. This is a more precise, empirically
confirmed root cause than "the deterministic generator never exercised the probabilistic
dependency edges" (the working hypothesis before this run existed): the missing piece is an
identifier bridge between `seqrefactor.datasets.graph_from_manifest`'s ground truth and
`seqrefactor.graph.builder.build`'s independently-derived instances, not the choice of generator.
Fixing it is out of scope here (it needs either the builder to key its derived ids the same way
the manifest does for these 15 generated subjects, or an explicit location-based lookup table) and
is recorded as a concrete follow-up in the paper's Threats to Validity.
