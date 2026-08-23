# REPO_MAP.md

Produced per the Claude Code Working Brief, Section 0 ("orient yourself before writing
code"). Summarises what exists in this repository today, what the brief asks for, and where
the brief's description of the paper diverges from the paper actually on disk.

**Status update:** on the repository owner's explicit instruction, Sections 1-8 of the brief
were subsequently implemented *against the brief*, ahead of the paper text — see Section 5
below for what was built and what remains. Sections 1-4 of this document are the original,
still-accurate pre-implementation snapshot and conflict flag; read them first for context.

## 1. What exists (mapped to the paper's own structure)

The repository already implements a working, tested, end-to-end version of the pipeline the
paper describes in Sections IV-VI, close enough that most of it reads as "done" rather than
"missing":

| Paper section | Repo module | Status |
|---|---|---|
| IV-A/B, Definition 1, Table I (prerequisite edges) | `seqrefactor/graph/builder.py`, `graph/rules.py` | Implemented: catalogue rules (5, matching paper Table I exactly) + structural co-location, edges carry provenance |
| IV-C, Eq. 1 (impact score) | `seqrefactor/order/impact.py` | Implemented: alpha/beta/gamma-weighted, normalised [0,1] |
| IV-D/E, Eq. 2-4, Definition 2 (ordering problem, cascading violation, NSR) | `seqrefactor/model.py` (`RunReport` computed fields), `orchestrator.py` | Implemented |
| V, Algorithm 1 (priority-queue Kahn + Tarjan SCC escalation) | `seqrefactor/order/orderer.py` | Implemented, with a dedicated golden test (`tests/golden/test_ordering.py`) asserting safety is never traded for priority |
| VI (agentic pipeline: detect/build/order/retrieve/generate/verify/gate/re-detect) | `seqrefactor/orchestrator.py` (LangGraph), `detect/`, `retrieve/`, `generate/`, `verify/`, `gate.py` | Implemented end-to-end; re-detects and rebuilds the graph every iteration ("the loop is the point") |
| VII (four-arm ablation: seqrefactor/impact-only/topo-only/unordered, two generators) | `orchestrator._select_ordering`, `cli.py run`, `report.py` | Harness runs all four strategies x two generators x subjects, seeded, writes content-hashed `RunReport` JSON |
| VIII (pilot: 8-smell synthetic module) | `datasets/synthetic/pilot_checkout_v1/` | Present, real compiled/tested Java source, drives integration tests |

36 tests collected (`uv run pytest --collect-only`); unit + golden + integration tiers.

Java sidecar (`jvm-sidecar/`, Gradle) provides real JUnit execution and CK metrics for the
five-family verification gate — this is genuine infrastructure, not a stub.

The README already contains an honest "What's real vs. what's thin" section that substantially
overlaps with what this document is meant to produce.

## 2. Gaps against the paper as currently written (Sections VII/VIII)

- **No non-parametric paired statistical tests.** `report.py::aggregate_by_strategy` computes
  per-strategy means only; the Wilcoxon/effect-size testing paper Section VII-D calls for is not
  implemented.
- **No RQ4 weight-sensitivity sweep execution.** `WeightSweep` exists in `Config`/CLI plumbing;
  the loop that actually runs it and records sensitivity is not implemented.
- **Corpus is far smaller than Section VII-C specifies.** Three synthetic subjects (acyclic,
  fully-cyclic, partially-cyclic) vs. the spec'd 20-45-file controlled tier; no open-source tier
  with `RefactoringMiner`-recovered reference orders.
- **No table/summary emission matching a `[RESULTS PENDING]` replacement workflow** — because
  the paper on disk does not contain `[RESULTS PENDING]` markers or Tables II-IV to replace (see
  Section 3 below).

## 3. Conflict: the brief describes a paper that isn't the one on disk

Per the brief's own instruction ("if any instruction here conflicts with what the paper says,
... flag the conflict rather than guessing"), this needs to be surfaced before any of Sections
2-6 of the brief are started, since they assume features that don't exist in either the paper or
the code:

| Brief says (Section 0/2/3/5/8) | Actual `SEQ_REFACTOR_paper.docx` (17 pages, read in full) |
|---|---|
| Section IV includes "signed positive/negative dependencies" | Section IV (Definitions 1-2, Eq. 1-4) has only prerequisite edges. No polarity, no per-edge probability, no positive/negative dependency table. |
| Section VI-A covers "incremental maintenance and session complexity" | Section VI has no subsection VI-A; it is four unlettered paragraphs (Detect and build / Order / Retrieve and generate / Verify and gate / Re-detect). No incremental-maintenance discussion anywhere in the paper. |
| RQ5, RQ6, H4, H5 (dependency-mass study, complexity instrumentation) | Paper Section VII-A defines only RQ1-RQ4 and H1-H3. There is no RQ5/RQ6/H4/H5. |
| Tables II, III, IV and five `[RESULTS PENDING]` markers to fill | No table appears anywhere in the 17-page paper (Section VIII "Preliminary Pilot" reports its one execution order in prose), and no `[RESULTS PENDING]` string occurs in the document. |
| Citations [32] (Marković), [33] (Pearce and Kelly), [34] (Marchetti-Spaccamela, Nanni, Rohnert) | The reference list ends at [31] (Palomba et al. 2018). [32]-[34] don't exist in this paper. |
| Contribution numbering C1 = signed graph, C6 = incremental maintenance ("the headline"), C7 = dependency-mass study | Paper's own contributions (Section I-A) are C1-C5: formal model, ordering algorithm, agentic architecture, controlled experimental design, directional pilot. There is no C6 or C7. |

This is not a minor wording mismatch — the brief's headline contribution (C6, incremental graph
maintenance with bit-for-bit equivalence to a from-scratch baseline) is the centerpiece of
Sections 3-4 of the brief, and it rests on paper content that doesn't exist in the document
supplied. Two explanations seem possible: (a) the brief was drafted against a later/different
draft of the paper than the one currently saved as `SEQ_REFACTOR_paper.docx`, or (b) the brief
describes intended future work that was never merged into the paper text. Either is plausible
and I don't want to guess which, since it changes the actual scope of implementation work
substantially (signed-edge model + incremental algorithm + new experiments vs. filling out
statistics/corpus for the ablation that's already implemented).

Note also: earlier in this session, a `git pull` (outside my control) fast-forwarded this repo
from `550209b` to `04ac472` during our conversation, which added the current
`SEQ_REFACTOR_paper.docx` — separately, `SEQ_REFACTOR_paper.tex`, `SEQ_REFACTOR_paper.docx.pdf`,
and `SEQ_REFACTOR_Software_Specification.docx` disappeared from disk (though still recoverable
from git, per your choice not to restore them). So there may be a newer `.tex`/`.docx` version
of the paper that reflects the brief's scope, which simply isn't present in this checkout right
now.

## 4. Recommendation (resolved)

The repository owner chose option 2: implement against the brief, ahead of the paper text. The
paper's own claims (Section I-A Contributions, Section IV-VII) still need matching updates
before submission — that was **not** done as part of this work (it is paper-editing, not code),
and the discrepancy in Section 3 above remains true of `SEQ_REFACTOR_paper.docx` as currently
saved.

## 5. What was implemented against the brief

All of the brief's Sections 1-8 that could be built without external infrastructure this
environment lacks (see the caveat below) are done, tested, and passing:

| Brief section | Deliverable | Where |
|---|---|---|
| §2 (C1) | Signed POSITIVE/NEGATIVE dependency catalogue + graph edges (soft, never gate feasibility) | `graph/rules.py`, `graph/builder.py`, `model.DepEdge` |
| §3 (C6, "the headline") | Incremental graph maintenance, proven bit-for-bit equivalent to a from-scratch rebuild *by construction*, not just by testing | `graph/incremental.py` (see its design-note docstring for what the real efficiency saving is and is not) |
| §3 acceptance check | Equivalence harness: Hypothesis property tests (random smell forests) + every synthetic subject, step by step | `tests/property/test_incremental_equivalence.py` |
| §4 (C2, C6) | Operation counters (vertex/edge touches, heap ops, order-renumbering) + median wall-clock timing + a synthetic |V|/step-count scaling study | `model.OperationCounters`/`ComplexityRecord`, `eval/complexity.py` |
| §5 (C7) | Dependency-mass study: weighted positive/negative mass, realised co-resolution/cascading events, H4 as a paired Wilcoxon test with an honest "insufficient data" outcome below 5 subjects | `eval/depmass.py` |
| §6 | H1-H3 as paired Wilcoxon tests + rank-biserial effect size + bootstrap CI over matched (subject, generator) cells; RQ4's alpha/beta/gamma sweep execution loop | `report.hypothesis_tests`, `eval/stats.py`, `eval/weight_sweep.py` |
| §7 | Injected positive/negative ground truth on `pilot_checkout_v1`'s manifest, so the dependency-mass study has ground truth to read | `datasets/synthetic/pilot_checkout_v1/manifest.yaml`, `seqrefactor/datasets.py` |
| §8 | Table II/III/IV as CSV+LaTeX+Markdown, `results/SUMMARY.md` stating H1-H5 support, one command (`make results` / `seqrefactor results`) regenerating all of it from a fixed seed | `eval/tables.py`, `cli.py`, `Makefile` |

**Environment note (resolved):** the base environment had a JRE but no full JDK (`javac`
unavailable). A portable Eclipse Temurin 21 JDK was downloaded to a scratch directory (no root
needed, `JAVA_HOME` pointed at it) to build the jvm-sidecar and verify everything end-to-end for
real, closing what was originally an unverified gap: **75/75 tests pass with zero skips**
(vs. 69 passing + 6 skipped without a sidecar), `seqrefactor results` produced all three tables
from genuine pipeline executions including Table II (the main ablation), and
`eval/weight_sweep.py`'s RQ4 loop was smoke-tested against a real sidecar-backed run. See README's
"Working-Brief additions" verification-log entry for the specific numbers, including a real
finding the run surfaced (the `impact_only` arm showing `ordering_validity=0.0` and
cascading violations on every step, exactly the paper's Section IV-E failure mode, while the
three dependency-aware/topology-respecting arms held `ordering_validity=1.0`).

## 6. Open-source subject added (post-Section-5 follow-up)

One real open-source subject, `datasets/opensource/json_java_v1` (a filtered, dependency-free
copy of stleary/JSON-java at a pinned commit — see its own `PROVENANCE.md` for exactly what was
kept/excluded and why), was added and run through the real ablation matrix
(`configs/opensource.yaml`, 12-step bounded run, 126 real smells detected across 26 classes). It
surfaced and led to fixing two genuine, pre-existing gaps unrelated to this specific subject:

1. `jvm-sidecar` only bundled the JUnit 5 engine; many real-world Java projects (this one
   included) still use JUnit 4. Fixed by adding the vintage engine + `mergeServiceFiles()` to
   `jvm-sidecar/build.gradle` (the latter matters: Shadow doesn't merge `META-INF/services` files
   by default, so without it, adding a second engine silently drops the first one's registration).
2. `seqrefactor/_sidecar.py`'s `run_tests` never set the JVM subprocess's working directory, so
   any subject test reading a fixture by a module-root-relative path failed regardless of which
   subject invoked it. Fixed by threading `cwd=module.path` through
   `verify/tests.py` -> `_sidecar.run_tests` -> `_invoke`, with `--src`/`--test-src`/`--classpath`
   resolved to absolute paths first (needed once `cwd` changes what a relative path resolves
   against).

A real, incidental correctness bug in this session's own earlier work was also caught here:
`report.Reporter.ablation()`'s `hypothesis_tests` entry held raw `PairedTestResult` dataclasses,
which broke `seqrefactor run`'s `summary.json` write with a `TypeError` the first time that CLI
command (as opposed to `seqrefactor results`, exercised earlier and unaffected since it goes
through `eval/tables.py` instead) was actually run end-to-end. Fixed with `dataclasses.asdict`
plus a regression test (`tests/unit/test_report.py::test_reporter_ablation_output_is_json_serializable`).

Real result (see `datasets/opensource/json_java_v1/PROVENANCE.md` for full detail): `impact_only`
(no topological safety) hit 5/12 cascading violations and 58% ordering validity on this subject;
`seqrefactor`/`topo_only`/`unordered` all held 0 violations and 100% validity. One subject, one
generator, 12 steps — illustrative, not a powered statistical claim, but real, on unmodified
production code, and directionally exactly what the paper's ordering-safety argument predicts.

**Still not done**: the open-source subject tier's own missing piece,
`RefactoringMiner`-recovered reference orders (needs real commit-history mining, a substantial,
separate effort), more open-source subjects beyond this one, and scaling the synthetic corpus to
the spec'd 20-45 files (the three checked-in synthetic subjects are small but fully exercised,
including the signed-edge ground truth).

## 7. Tables III and IV committed (post-Section-6 follow-up)

A separate paper-writing session/agent reported back (relayed by the repository owner) that it
correctly refused to fabricate statistics for Tables V/VI (that document's own numbering for the
dependency-mass and complexity-scaling results) rather than invent numbers not backed by this
repository — the right call, and consistent with everything above. It described those tables as
"not yet computed... genuinely not in the repository." That was accurate about *committed output*
but not about the underlying capability: `eval/depmass.py` and `eval/complexity.py` were already
real, tested, working modules (Section 5 above); the numbers simply hadn't been generated and
preserved anywhere version-controlled, the same situation Table II was in before Section 6.

Closed the same way: ran both against real inputs and committed the output under `evaluation/`
(see `evaluation/README.md` for exact commands, full tables, and scope caveats) —

- **Table III** (dependency-mass, `eval/depmass.py`, structural only, no executed run threaded
  through): real per-subject positive/negative mass from each synthetic manifest's ground truth.
  H4 correctly reports `n=3, supported=None` ("insufficient... minimum 5") — no p-value, no
  effect size, none fabricated.
- **Table IV** (complexity-scaling, `eval/complexity.py`, synthetic seeded study across
  |V| ∈ {10, 25, 50, 100, 200}): real operation counters showing the predicted H5 scaling
  signature — from-scratch edge touches grow roughly quadratically with |V|, incremental edge
  touches stay roughly flat, and the ratio between them grows from ~8x at |V|=10 to **~10,600x at
  |V|=200**.

Both are one-shot, deterministic, seeded computations (not requiring the jvm-sidecar), reusing
the exact production code path `seqrefactor results` already calls — nothing was manually
reconstructed or estimated.

## 8. Phase 2: the synthetic-subject generator and the powered study

See `PHASE2_PLAN.md` for the pre-implementation gap list (Section 0's required deliverable) and
`REPRODUCE.md` for exact reproduction steps. Summary of what changed:

- **`seqrefactor/synth/generator.py`**: a deterministic, seeded generator planting each smell as a
  real, compilable Java structural pattern the native detector and graph builder independently
  rediscover from source (never from the manifest) — the anti-circularity property the brief
  named directly. Plants only the four categories the native detector actually supports (GodClass,
  LongMethod, MessageChains, BigSwitch); Feature Envy and other catalogue-only categories are
  explicitly out of scope, stated in the generator's own SCOPE NOTE rather than silently narrowed.
  Cycle subjects carry a manifest-declared cycle (the containment-based builder cannot discover a
  real one, by construction — see the generator's CYCLE NOTE). All acceptance checks (§1.6:
  determinism, compile/test-green, independence with overlap, cycle control) hold and are covered
  by `tests/unit/test_synth_generator.py`.
- **`seqrefactor/synth/build_corpus.py`**: generates 15 subjects from one master seed across a
  documented size x density grid plus cycle/signed-rate variants; `datasets/synthetic/CORPUS.md`
  documents every one. Combined with the 3 pre-existing hand-written subjects, the corpus is 18
  subjects (Definition of Done: "at least 15").
- **`order/search_based.py`**: a fifth strategy arm, a real genetic algorithm searching for the
  paper's own optimisation objective (Eq. 2) via a priority-vector encoding decoded through the
  existing, already-safe `orderer.order` (so search can never produce an unsafe ordering, by
  construction). Explicitly documented as *not* a verified reproduction of Ouni et al. [29] or Liu
  et al. [30]'s exact published algorithms (this environment cannot fetch either paper to check
  fidelity) — see its own HONESTY NOTE.
- **The powered ablation ran for real**: 18 subjects x 5 strategies, `configs/synthetic.yaml`,
  raw run reports committed under `datasets/synthetic/example_run/`. H3 and H4 now compute real
  statistics at n=18 (previously "insufficient data" at n=3). H1/H2 are honestly **degenerate**
  (every paired difference is exactly zero, not merely non-significant) — traced to a real,
  reported mechanism: the baseline generator cannot patch class-level smells, so most of the
  bounded step budget on multi-GodClass subjects goes to rejected attempts before any real
  progress is possible. See `evaluation/README.md`'s Phase 2 section for the full, honest
  narrative, including why `impact_only`'s designed failure mode barely triggers on the *generated*
  corpus specifically (a real generator-severity-design limitation, stated plainly, not hidden).
- **Tables III (dependency-mass) and IV (complexity) re-run against the full corpus**, the latter
  now also measured against real corpus subject graphs (`eval/complexity.run_corpus_study`), not
  only the synthetic |V| sweep — both corroborate the same asymptotic trend independently.
- **Not done, stated plainly**: the LLM-generator run (Section 3, step 3) needs
  `OPENAI_API_KEY`, absent in this environment — everything above uses the baseline generator
  only, so `net_smell_resolution` being flat at 0 reflects that generator's real limitations, not
  necessarily SEQ-REFACTOR's ordering algorithm. `REPRODUCE.md` states exactly how to close this
  gap once a key is available.
