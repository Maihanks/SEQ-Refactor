# PHASE2_PLAN.md

Produced per the Claude Code Working Brief, Phase 2, Section 0. What exists today, what this
phase adds, per section. Read `REPO_MAP.md` first (Phase 1's equivalent document); this one
assumes it.

## Current corpus state (Section 0.2)

- `datasets/synthetic/`: three hand-written subjects (`pilot_checkout_v1`, `billing_cycle_v1`,
  `notification_mixed_v1`), only `pilot_checkout_v1` has real compilable Java source and JUnit
  tests; the other two are graph-only manifest fixtures (no `src/`).
- `datasets/opensource/`: one real subject, `json_java_v1` (filtered stleary/JSON-java), with a
  committed example ablation run under `example_run/`.
- `evaluation/`: Table III (dependency-mass) and Table IV (complexity-scaling), computed against
  the existing corpus, committed with an honest scope note (structural mass only, no realised
  events threaded through; synthetic seeded scaling study, not the real subjects).

## Manifest schema (Section 0.3)

From `datasets/synthetic/pilot_checkout_v1/manifest.yaml`, read by `seqrefactor/datasets.py`
(`load_manifest`, `graph_from_manifest`, `expected_cycle_members`):

```yaml
subject: <str>
acyclic: <bool>
smells:
  - { id: <str>, category: <str>, loc: [<qualified.name>], severity: <float> }
prerequisites:
  - { src: <id>, dst: <id> }
expected_cascade_if_out_of_order:
  - <free-text label>
positive_dependencies:
  - { src: <id>, dst: <id>, probability: <float>, operation: <str> }
negative_dependencies:
  - { src: <id>, dst: <id>, probability: <float>, operation: <str> }
```

The generator (Section 1) must emit exactly this shape so `seqrefactor.datasets` consumes it
unchanged, with zero changes to that loader.

## Section-by-section: what exists, what this phase adds

| Section | What exists | What this phase adds |
|---|---|---|
| 1, generator | Nothing — no `seqrefactor/synth/` package exists yet. `graph/builder.py`'s containment + catalogue-rule edge derivation exists and is independent of any manifest (it only ever reads `SmellInstance` objects passed to it, never a manifest file) — so the independence acceptance check is really about the *generator* correctly planting structure the builder can rediscover, not about changing the builder. | `seqrefactor/synth/generator.py`: deterministic Java+manifest generator, planting each smell as a real structural pattern (see brief §1.3), with the independence property built in by construction (ground truth is derived from what was actually planted into the AST/text, the builder is never told). |
| 2, corpus | 3 synthetic + 1 open-source subject total. | `seqrefactor/synth/build_corpus.py`, a documented parameter grid, `configs/synthetic.yaml`, `CORPUS.md`. |
| 3, ablation + stats | `eval/stats.py`/`report.hypothesis_tests` already implement the real Wilcoxon + rank-biserial + bootstrap-CI machinery (Phase 1) and already correctly return `supported=None` below `n=5`. Nothing to build here except *subjects*. | Run `seqrefactor results`/`run` against the generated corpus; commit `summary.json` + per-strategy `RunReport`s under a tracked path (not gitignored `results/`/`runs/`, matching the `example_run/`/`evaluation/` convention already established). |
| 4, search-based baseline | Only 4 strategies exist (`orchestrator._select_ordering`). No search-based scheduler. | A 5th strategy, citing one real method from the papers already in the reference list ([29] Ouni et al. or [30] Liu et al.). Honesty note now, to avoid over-claiming later: this environment cannot fetch either paper's exact pseudocode to verify byte-for-byte fidelity, so the implementation will be a real, working algorithm in the cited paper's general family (for a multi-objective/genetic scheduler, that means an actual population-based search over orderings scored by the five-family metrics already computed here), documented honestly as such in the module docstring, not presented as a verified reproduction. Same principle already applied to `graph/incremental.py` regarding Pearce-Kelly in Phase 1. |
| 5.1, Table VI (complexity) | `evaluation/table4_efficiency.*` exists, but only for the *synthetic seeded scaling study* (`eval/complexity.py`'s own |V| sweep), not measured against the actual generated corpus. | Re-run (or extend) against the real generated corpus's actual graphs, alongside the existing scaling study — both are legitimate, complementary views (one controlled/synthetic-|V|, one "real corpus as it stands"). |
| 5.2, Table V (dependency-mass) | `evaluation/table3_depmass.*` exists but with `co_resolution_events`/`cascading_violation_events` at 0 for every subject, since no executed `RunReport` was threaded through (Phase 1's honest scope note). | Once Section 3's real ablation runs exist, pass them into `eval/depmass.run_study` so realised events are non-zero where they actually occurred, and only where the generator planted `positive_dependencies`/`negative_dependencies` (Section 1 must do this for every generated subject, not just one, unlike the current single hand-edited `pilot_checkout_v1`). |
| 6, wiring | `eval/tables.py`, `seqrefactor results`, `Makefile` already exist and already emit exactly this shape (Phase 1). | Point them at the corpus; commit output; write `REPRODUCE.md`. |

## Cost/scope planning (not in the brief, added here because it governs what's actually
## achievable)

Every real ablation step costs one full sidecar compile+test cycle (~2-10s depending on subject
size, measured in Phase 1 against `json_java_v1`: ~4.6s for 445 tests across 78 files). With N
subjects x 5 strategies x k steps, wall-clock is N x 5 x k x (a few seconds). To keep a corpus run
inside a reasonable session:

- Generated subjects will be kept small (`n_classes` in roughly 5-15, not the brief's full
  suggested 8-25 range at the top end) so each subject's own test suite stays fast.
- `max_steps` will be bounded per subject (not left at the default 50), sized to each subject's
  actual smell count rather than a single global constant, mirroring `configs/opensource.yaml`'s
  own reasoning.
- The LLM-generator run (Section 3, step 3) needs `OPENAI_API_KEY`, which is not present in this
  environment (confirmed in Phase 1: no `.env` file). It is out of scope until a key is supplied;
  everything else in this phase uses the deterministic baseline generator only, exactly as
  Phase 1 did throughout.

## Standing constraints carried over from the brief

No em-dashes in code/comments/docs/generated text (commas or parentheses instead). No fabricated,
hand-edited, or hard-coded results anywhere; every number must trace to a script and a seed. The
incremental algorithm's bit-for-bit equivalence to from-scratch is non-negotiable and already
enforced by `tests/property/test_incremental_equivalence.py`; the generator and corpus must not
weaken that guarantee (they exercise the ordering algorithm on new graphs, not change it).
