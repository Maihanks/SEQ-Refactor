# SEQ-REFACTOR

**A stateful agentic pipeline for impact-forward, dependency-safe ordering of multi-smell refactorings.**

SEQ-REFACTOR resolves the code smells of a decaying Java module in an order that is both
**dependency-safe** (no smell is refactored before its structural prerequisites) and
**impact-forward** (high-value smells are brought as early as the dependencies allow). It models
a module's detected smells as a directed **smell-dependency graph**, computes a normalised
**impact score** per smell over coupling, complexity, and co-occurrence, and finds a
dependency-respecting, impact-forward execution agenda with a priority-queue formulation of
Kahn's algorithm — escalating any genuine dependency cycle to a human via Tarjan
strongly-connected-component decomposition rather than resolving it blindly.

That ordering algorithm is the paper's contribution and this repository's core. Everything else
(detection, retrieval, generation, verification) is real, working, end-to-end infrastructure
built around it, scoped honestly rather than over-claimed — see [What's real vs. what's
thin](#whats-real-vs-whats-thin) below.

Companion documents (`draft docs/`):
[`SEQ_REFACTOR_paper.tex`](draft%20docs/SEQ_REFACTOR_paper.tex) — the research paper this
implements — and
[`SEQ_REFACTOR_Software_Specification.docx`](draft%20docs/SEQ_REFACTOR_Software_Specification.docx)
— the engineering specification this codebase follows section-by-section.

## Table of contents

- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
- [Running the pipeline](#running-the-pipeline)
- [Testing](#testing)
- [Datasets](#datasets)
- [Configuration and secrets](#configuration-and-secrets)
- [Verification log](#verification-log-what-was-actually-run-and-when)
- [What's real vs. what's thin](#whats-real-vs-whats-thin)
- [Traceability to the specification](#traceability-to-the-specification)
- [License](#license)

## Architecture

A single state object (module, current smell-dependency graph, metric baseline, agenda) is
threaded through seven stages, orchestrated with [LangGraph](https://github.com/langchain-ai/langgraph)
so the loop is real, not simulated (`seqrefactor/orchestrator.py`):

```
S1 DETECT      tree-sitter-backed heuristic analyser -> SmellInstance[]
               |- precondition: test coverage >= configured threshold (seqrefactor/ingest.py)
               '- emits: SmellInstance[]

S2 BUILD       catalogue precedence rules + structural containment
               '- emits: SmellDependencyGraph (edges carry provenance, OR-5)

S3 ORDER       <== THE CONTRIBUTION
               priority-queue Kahn (impact-forward, dependency-safe)
               + Tarjan SCC decomposition of residual cycles
               '- emits: Agenda (ordered) + Escalations (SCCs, human review)

S4 RETRIEVE    TF-IDF / OpenAI-embedding vector search + in-memory code-property graph
               '- emits: GenContext

S5 GENERATE    deterministic Extract-Method baseline | OpenAI LLM adapter
               patch evaluated in an isolated temporary-directory copy
               '- emits: Candidate

S6 VERIFY      five-family metric delta + JUnit test suite (via jvm-sidecar) +
               architectural constraint check
               '- emits: Evidence

S7 GATE        accept -> promote patch + RE-DETECT (loop back to S1)
               reject -> discard candidate, module untouched, log + continue
               '- emits: Verdict, RunReport
```

**The loop is the point.** After every step the analyser re-runs on the current module state and
the agenda is recomputed from scratch over whatever is still unresolved — this is what keeps the
plan correct as structure changes, and it is exactly the state-tracking whose absence the
RefactorBench paper identifies as the dominant failure mode of autonomous multi-file refactoring.

### The ordering algorithm

```python
# seqrefactor/order/orderer.py
ready = max-heap of {v : indegree(v) == 0}, keyed by impact
while ready:
    v = extract-max(ready)          # highest-impact eligible smell
    agenda.append(v)
    for successor w of v:
        indegree[w] -= 1
        if indegree[w] == 0: push w onto ready
# residual (cyclic) vertices -> Tarjan SCC -> escalate, never break automatically
```

Safety (a smell only becomes eligible once every prerequisite is resolved) and priority
(the eligible smell with the highest impact score is always chosen next) are unified in one
traversal, in `O((|V|+|E|) log|V|)` time. **Safety is never traded for priority** — this
invariant is guarded by [`tests/golden/test_ordering.py`](tests/golden/test_ordering.py), the
single most important test in the system, which runs against every synthetic subject's
ground-truth dependency structure and asserts a higher-impact smell is *never* placed before an
unresolved prerequisite.

## Repository layout

```
seqrefactor/                 the Python package (installed into .venv by `uv sync`)
  model.py                   pydantic data model (§6 of the spec) shared by every stage
  ingest.py                  module loading + coverage precondition
  cli.py                     `seqrefactor run|order|reproduce`
  orchestrator.py            the LangGraph S1..S7 pipeline + re-detect loop
  gate.py                    accept/reject evidence fusion
  report.py                  ablation tables, per-step trajectory
  detect/
    native.py                tree-sitter heuristic SmellDetector (works with zero setup)
    sonar.py                 SonarQube Web API adapter (real client; needs a live server)
  graph/
    builder.py                catalogue rules + structural containment -> DepEdge[]
    rules.py                  the precedence rule table (paper Table I)
  order/
    impact.py                  impact scoring (Eq. 1)
    orderer.py                  <== the ordering algorithm (THE CONTRIBUTION)
  retrieve/
    vector.py                  TF-IDF (offline) / OpenAI-embedding semantic retrieval
    cpg.py                      in-memory call-graph structural retrieval
    retriever.py                 fuses both into GenContext
  generate/
    baseline.py                 deterministic Extract-Method-wrapper generator (ablation control)
    llm.py                      OpenAI adapter with record/replay caching (NFR-2)
  verify/
    metrics.py                   five-family metric facade (tree-sitter + CK-via-sidecar)
    tests.py                     JUnit execution via jvm-sidecar
    arch.py                      interface-surface + package-cycle check
  _sidecar.py, _treesitter.py, _worktree.py   internal shared helpers

jvm-sidecar/                 Java 17 / Gradle sidecar: JUnit execution + CK metrics
  README.md                  build/run/JSON-schema documentation for the sidecar specifically

datasets/synthetic/          ground-truth synthetic subjects (see Datasets below)
configs/                     smoke.yaml, synthetic.yaml, ablation.yaml
tests/
  golden/                    the ordering golden test (§9.2) — guards OR-1..OR-3
  unit/                      one file per module above
  integration/               full-pipeline, real-sidecar, scratch-copy end-to-end tests
  support.py                 manifest-loading test helpers, independent of the code under test

pyproject.toml               dependencies, dev tooling (`[dependency-groups]`), pytest/ruff/mypy config
uv.lock                      exact resolved/pinned dependency versions (committed; see Getting started)
```

## Getting started

Prerequisites: **[uv](https://docs.astral.sh/uv/)** (manages the Python interpreter, virtual
environment, and locked dependencies — no manual `venv`/`pip` needed), **JDK 17+** (for the
sidecar), network access for the first `uv sync` and Gradle build (downloads from PyPI / Maven
Central) and for the OpenAI adapter.

Install uv once, if you don't have it: `pip install uv` (or the standalone installer at the link
above) — after that, uv itself manages everything Python, including which interpreter to use.

```bash
# 1. Python environment: creates .venv and installs every dependency at the exact
#    versions pinned in uv.lock (commit uv.lock; never commit .venv)
uv sync --group dev

# 2. Java sidecar (required for real test execution / CK metrics; see jvm-sidecar/README.md)
cd jvm-sidecar
./gradlew build                 # gradlew.bat on Windows
cd ..

# 3. Secrets (optional — only needed for the LLM generator / SonarQube adapter)
cp .env.example .env
# edit .env and set OPENAI_API_KEY if you want the LLM generator to do live calls;
# everything else (ordering, the deterministic baseline generator, the native detector,
# the sidecar) works with no keys and no network.

# 4. Verify
uv run pytest -q
```

`uv run <cmd>` executes `<cmd>` inside the project's `.venv` without activating it manually — use
it for every command below (`uv run pytest`, `uv run seqrefactor ...`, `uv run python ...`). To
add a new dependency: `uv add <package>` (or `uv add --group dev <package>` for a dev-only tool),
which updates `pyproject.toml` and `uv.lock` together — don't hand-edit `uv.lock`.

## Running the pipeline

```bash
# Read-only: print the computed agenda and any escalations for one subject
uv run seqrefactor order --config configs/smoke.yaml datasets/synthetic/pilot_checkout_v1

# Full pipeline run: mutates its target module in place (it's a refactoring tool) —
# NEVER point --config subjects_glob at the checked-in datasets/ directly unless you
# intend to refactor them for real. Copy the subject first:
cp -r datasets/synthetic/pilot_checkout_v1 /tmp/scratch_subject
uv run seqrefactor run --config configs/smoke.yaml   # edit subjects_glob first, or pass your own config
```

`seqrefactor run` writes one content-hashed JSON `RunReport` per (subject, strategy, generator)
cell plus a `summary.json` aggregate to `runs/` (gitignored — it's regenerable output, not
source). `seqrefactor reproduce <run_report.json>` recomputes the derived measures (net smell
resolution, cascading violations, ordering validity, escalation rate) from a persisted report and
confirms they match what's stored, which is the reproducibility story NFR-2/NFR-3 exist for.

## Testing

```bash
uv run pytest -q                          # everything (36 tests at last count)
uv run pytest tests/golden -q             # the ordering golden test only
uv run pytest tests/unit -q               # unit tests (most run with zero external setup)
uv run pytest tests/integration -q        # full pipeline, real sidecar, ~30s (needs jvm-sidecar built)
```

Tests that need the built sidecar jar (`tests/unit/test_verify_sidecar.py`,
`tests/integration/*`) skip themselves cleanly with a clear reason if it isn't present, rather
than failing — check `jvm-sidecar/README.md` if you see skips and want them to run.

Every integration/e2e test operates on a `tmp_path` copy of the relevant dataset, never on
`datasets/synthetic/` directly, since the orchestrator's job is to mutate its target module —
running it against the checked-in ground-truth fixtures would corrupt them.

## Datasets

Three synthetic subjects under `datasets/synthetic/`, each with a `manifest.yaml` declaring its
*ground-truth* smell-dependency structure (used by the golden test, independent of what the real
detector/graph-builder produce from source — see `tests/support.py`):

| Subject | Structure | Purpose |
|---|---|---|
| `pilot_checkout_v1` | Acyclic; a God Class (`OrderService`) containing 6 method-level smells | The only subject with real, compiled, tested Java source (`src/`) — mirrors the paper's illustrative pilot and drives every end-to-end/integration test |
| `billing_cycle_v1` | A genuine 3-node cycle (`s1 -> s2 -> s3 -> s1`) | Exercises full SCC escalation (§8.1: "include at least one subject with a deliberate dependency cycle") |
| `notification_mixed_v1` | A 2-node cycle plus a dependent and an independent smell | Exercises *partial* escalation: the cycle escalates while the acyclic remainder still gets ordered |

The spec's full experimental design (§8) calls for 20–45-file injected-smell Java modules across
a controlled synthetic tier and an open-source tier with mined reference orders. What's shipped
here is a smaller, real, fully-exercised subset — every code path (ordering, escalation, partial
escalation, detection, verification, generation) has at least one genuine test against it — rather
than a larger but shallow corpus. Scaling the synthetic tier to the full spec'd size, and adding
the open-source tier with `RefactoringMiner`-recovered reference orders, is the natural next step
(§8.2) and is not done here.

## Configuration and secrets

`.env` (gitignored, never commit it) configures optional integrations; copy `.env.example` to
start. Everything not set falls back to a working, offline default:

| Variable | Used by | If unset |
|---|---|---|
| `OPENAI_API_KEY` | `seqrefactor/generate/llm.py`, `seqrefactor/retrieve/vector.py` | LLM generator raises a clear error unless a cached response already exists; vector retrieval falls back to TF-IDF |
| `SEQREFACTOR_LLM_MODEL` | LLM generator | defaults to `gpt-4.1-mini` |
| `SEQREFACTOR_SEED` | dataset/generation seeding | defaults to `20260101` |
| `SONARQUBE_URL`, `SONARQUBE_TOKEN` | `seqrefactor/detect/sonar.py` | that adapter is simply unused; `seqrefactor/detect/native.py` is the default detector and needs neither |

## Verification log (what was actually run, and when)

In the spirit of the spec's own honesty notes, here is what was concretely exercised while
building this repository, not just written:

- **Ordering algorithm** — golden test passes on all three synthetic subjects (acyclic,
  fully cyclic, partially cyclic), including the anti-priority-override meta-test.
- **Java sidecar** — `gradle build` and `gradle test` pass; the built fat jar was invoked
  directly against `pilot_checkout_v1` for both the `metrics` and `test` subcommands and
  produced correct, sane output (CK flagged `OrderService` with far higher CBO/LCOM/WMC/RFC than
  any other class — it's the God Class by construction).
- **Deterministic baseline generator** — its patch was applied to a scratch copy of
  `pilot_checkout_v1` and recompiled + retested through the real sidecar: compiles, 4/4 tests
  pass.
- **OpenAI LLM adapter** — a real API call was made (model `gpt-4.1-mini`) to confirm the
  configured key works; the full `generate.llm.refactor()` path was exercised end-to-end,
  its output located the correct source file (after a real bug in the naive
  substring-based file-resolution heuristic was found and fixed), and the resulting patch was
  compiled and tested through the real sidecar: compiles, 4/4 tests pass. Cache/replay
  (NFR-2) was verified by deleting `OPENAI_API_KEY` from the environment and confirming a
  second call for the same (target, context, seed, model) returns byte-identical output with
  no network access.
- **Full orchestrator loop** — run end-to-end against a scratch copy with the baseline
  generator; separately verified that a forced-rejected candidate leaves the module file
  byte-for-byte unchanged (NFR-1), and that `GodClass` is always ordered before every
  method-level smell it structurally contains, through the real detector + graph builder +
  orderer + LangGraph loop (not just the manifest-driven golden test).
- **SonarQube adapter** (`seqrefactor/detect/sonar.py`) — **not** verified against a live
  server: none was reachable on `localhost:9000` in the environment this was built in, and no
  `sonar-scanner` binary was found. The client is a complete, real HTTP implementation against
  SonarQube's documented Issues Search API, but treat it as *implemented, not verified* until
  run against a real instance.

## What's real vs. what's thin

Being direct about scope, matching the spec's own "SCOPE NOTE" and "HONESTY NOTE" pattern:

- **Real and the actual contribution**: the smell-dependency graph, impact scoring, the
  priority-queue-Kahn + Tarjan-SCC ordering algorithm, and its golden test. This is what the
  paper is about, and it has no shortcuts.
- **Real and fully working, but intentionally modest in scope**:
  - The native detector (`detect/native.py`) is a threshold-based heuristic over tree-sitter,
    not a claim of state-of-the-art smell detection — it's a real, swappable `SmellDetector`
    implementation that needs no external tooling.
  - The deterministic baseline generator wraps a target method's body in a delegating call
    rather than performing a semantically meaningful extraction — it exists as the ablation's
    non-LLM control (§8.3's "Variables"), not as a quality refactoring tool.
  - Retrieval's structural half (`retrieve/cpg.py`) resolves calls by simple name matching, no
    type inference, so it can conflate same-named methods on unrelated classes.
  - Isolation (`_worktree.py`) uses a plain temporary-directory copy rather than a literal `git
    worktree` — the isolation guarantee NFR-1 asks for (fresh, disposable copy; a rejected
    candidate never touches the real module; no state leaks between candidates) holds either
    way, and a literal worktree was tried first and rejected because `git worktree add` only
    ever sees committed history, which silently breaks on an uncommitted or newly-added subject
    module.
- **Real client code, unverified against a live server**: the SonarQube adapter (see
  Verification log above).
- **Not implemented**: the open-source-subjects tier with `RefactoringMiner`-recovered
  reference orders, the full 20–45-file synthetic corpus, the α/β weight-sweep runner for RQ4
  (the config schema and CLI plumbing for it exist; the sweep-execution loop itself doesn't),
  and non-parametric paired statistical testing over ablation results (`report.py` produces the
  descriptive per-strategy means those tests would run over, not the tests themselves).

## Traceability to the specification

Every module's docstring cites the specification section and, where relevant, the paper
definition or equation it implements (e.g. "Eq. 1", "OR-1..OR-3", "NFR-2"), so a reviewer can
audit the mapping module-by-module without a separate crosswalk document.

## License

MIT — see `pyproject.toml`. Add a `LICENSE` file with the full text before treating this as a
formal release; none is included yet.
