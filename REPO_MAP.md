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

**Still not done** (matches this document's original Section 2 gap list, now narrower): the
open-source subject tier with `RefactoringMiner`-recovered reference orders, and scaling the
synthetic corpus to the spec'd 20-45 files (the three checked-in subjects are small but fully
exercised, including the new signed-edge ground truth). Both are substantial, separate efforts
(cloning/mining real repositories) out of scope for this increment.
