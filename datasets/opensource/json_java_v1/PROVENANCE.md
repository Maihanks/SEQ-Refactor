# json_java_v1 — provenance and reproduction

The paper's experimental design (§VII-C) calls for an open-source subject tier alongside the
controlled synthetic tier. This is the first (and, in this increment, only) open-source subject:
a filtered copy of [stleary/JSON-java](https://github.com/stleary/JSON-java), a small,
single-purpose, dependency-free Java JSON library, chosen specifically because it fits the
jvm-sidecar's compile model (`seqrefactor/_sidecar.py`, `jvm-sidecar/TestRunnerCommand.java`),
which compiles subject source directly with `javac` against an explicit classpath rather than
resolving Maven/Gradle dependencies — a subject with runtime dependencies beyond JUnit would need
those dependencies fetched and wired in manually.

## Source

- Repository: <https://github.com/stleary/JSON-java>
- Commit: `6c140480797ad70a41df84bc8ebab405ca44656b` (`master`, 2026-08-14)
- License: Public Domain (`LICENSE` in this directory, copied verbatim from the source repo)

## Reproduce the fetch

```bash
git clone https://github.com/stleary/JSON-java.git
cd JSON-java
git checkout 6c140480797ad70a41df84bc8ebab405ca44656b
```

## What was kept, and why

| Kept | Count | Notes |
|---|---|---|
| `src/main/java/org/json/*.java` | 26 | Unmodified, entire main source tree |
| `src/test/java/org/json/junit/*.java` (+ `data/` fixtures) | 52 | See exclusions below |
| `src/test/resources/` | verbatim | Needed by `JSONParserConfigurationTest`, which reads fixture files by a path relative to the module root |
| `LICENSE` | verbatim | |

**7 of the original 59 test files were excluded**, each for a concrete, mechanical reason tied to
the jvm-sidecar's current capabilities rather than anything about the code itself:

- `JSONObjectTest.java`, `CookieListTest.java`, `JSONStringerTest.java`, `EnumTest.java`,
  `JSONArrayTest.java` (5 files) — depend on `org.mockito:mockito-core` and/or
  `com.jayway.jsonpath:json-path`, test-scoped dependencies beyond JUnit that the sidecar's
  classpath does not provide (see the compile-model note above). The production classes these
  files exercise (`JSONObject.java`, `JSONArray.java`, etc.) are still present in main source and
  still detected/ordered/refactored by the pipeline — only their *own dedicated* test coverage is
  reduced; other retained test files still exercise `JSONObject`/`JSONArray` indirectly.
- `JSONPointerTest.java`, `XMLTest.java` (2 files) — read a fixture via
  `getClass().getClassLoader().getResourceAsStream(...)`, a classpath-relative (not
  filesystem-relative) lookup. The sidecar's `TestRunnerCommand.compile()` compiles `.java`
  sources into a temp output directory but does not copy non-`.java` resources onto that output's
  classpath (the way a Maven `process-test-resources` / Gradle `processTestResources` step
  would). This is a real, generalisable sidecar limitation, not specific to these two files;
  fixing it (making the sidecar copy `src/test/resources/**` onto the compiled classpath) is
  future work if a later subject needs it.

Net result, verified against the built sidecar: **445 tests, 441 passing, 0 failing** (4 tests
skipped upstream via `@Ignore`, not excluded by this filtering).

## A real sidecar bug this subject surfaced and fixed

Loading this subject exposed two genuine, pre-existing gaps in `jvm-sidecar`/`_sidecar.py`, not
specific to this repository, fixed as part of adding it (see their own commit history / code
comments for detail, not re-explained here):

1. `jvm-sidecar` bundled only the JUnit 5 (Jupiter) engine; this subject's tests are JUnit 4-style
   (`org.junit.Test`). Fixed by adding `junit:junit` + `org.junit.vintage:junit-vintage-engine` to
   `jvm-sidecar/build.gradle`, with `shadowJar { mergeServiceFiles() }` — without the latter, the
   Shadow plugin keeps only one engine's `META-INF/services` registration and silently drops the
   other.
2. `seqrefactor/_sidecar.py`'s `run_tests` never set the JVM subprocess's working directory, so a
   subject test reading a fixture by a module-root-relative path (`src/test/resources/...`, as
   `JSONParserConfigurationTest` does) failed regardless of which subject invoked it — the pilot
   synthetic subject simply never had a test like that, so the gap was invisible until now. Fixed
   by passing `cwd=module.path` through `verify/tests.py` -> `_sidecar.run_tests` -> `_invoke`,
   with `--src`/`--test-src`/`--classpath` resolved to absolute paths first (a relative path
   would otherwise resolve against the *new* cwd instead of the caller's).

## Reproducing the filtering

```bash
git clone https://github.com/stleary/JSON-java.git /tmp/json-java
cd /tmp/json-java && git checkout 6c140480797ad70a41df84bc8ebab405ca44656b

DEST=datasets/opensource/json_java_v1   # from this repo's root
mkdir -p "$DEST/src/main/java/org/json" "$DEST/src/test/java/org/json/junit/data"
cp /tmp/json-java/src/main/java/org/json/*.java "$DEST/src/main/java/org/json/"
cp /tmp/json-java/LICENSE "$DEST/LICENSE"
cp -r /tmp/json-java/src/test/java/org/json/junit/data/*.java "$DEST/src/test/java/org/json/junit/data/"
cp -r /tmp/json-java/src/test/resources "$DEST/src/test/resources"
for f in /tmp/json-java/src/test/java/org/json/junit/*.java; do
  base=$(basename "$f")
  case "$base" in
    JSONObjectTest.java|CookieListTest.java|JSONStringerTest.java|EnumTest.java|JSONArrayTest.java|JSONPointerTest.java|XMLTest.java) continue ;;
  esac
  cp "$f" "$DEST/src/test/java/org/json/junit/"
done
```

## Verifying it still passes

```bash
cd jvm-sidecar && ./gradlew build && cd ..   # needs the JUnit4/vintage-engine change above
uv run python -c "
from pathlib import Path
from seqrefactor import ingest
from seqrefactor.verify.tests import SidecarTestRunner
module = ingest.load(Path('datasets/opensource/json_java_v1'))
result = SidecarTestRunner().run(module)
print(result.success, result.tests_run, result.tests_passed, result.tests_failed)
"
# expect: True 445 441 0
```

## Ground truth

Unlike the synthetic subjects (`datasets/synthetic/*/manifest.yaml`), this subject has **no
hand-declared ground-truth dependency structure or reference resolution order** — it is real
code, not an injected-smell fixture, so there is no "correct" order to compare against except a
mined one. This subject is therefore used for the ablation matrix (comparing ordering strategies
against each other on cascading-violation count, net smell resolution, and ordering validity),
not for the golden ordering test or the dependency-mass study, both of which need declared ground
truth. Recovering a real reference order via `RefactoringMiner` against this project's actual
commit history remains out of scope for this increment (see REPO_MAP.md).

## Results: a real, 12-step ablation run

Run 2026-08-23 against the real sidecar (portable Temurin 21 JDK, see main README), config
`configs/opensource.yaml` (`max_steps: 12`, baseline generator, all four ordering strategies),
against a scratch copy of this subject. Detection found **126 smells** across the 26 real classes
(14 GodClass, 104 LongMethod, 5 BigSwitch, 3 MessageChains) -- far more than 12 steps can resolve,
so this is a bounded, illustrative early-session snapshot, not an exhaustive run (raise
`max_steps` for a fuller one; expect it to take much longer, see the timing note above).

| Strategy | net_smell_resolution | cascading_violations | ordering_validity | escalation_rate |
|---|---|---|---|---|
| `seqrefactor` | **1** | **0** | **1.0** | 0.0 |
| `impact_only` | 0 | **5** | **0.583** | 0.0 |
| `topo_only` | 0 | 0 | 1.0 | 0.0 |
| `unordered` | 0 | 0 | 1.0 | 0.0 |

**What actually happened, step by step** (all four strategies): the deterministic baseline
generator cannot produce a patch for a class-level smell at all (it only knows how to wrap a
*method* body, see `generate/baseline.py`), so every strategy's first several steps hit the
subject's 7 real `GodClass` instances (`JSONObject`, `JSONArray`, `JSONTokener`, `XML`,
`XMLTokener`, `JSONWriter`, `CDL`) in turn and reject them with `"generator produced no patch"`
-- burning more than half the 12-step budget before any method-level smell is even attempted.
This is a real, structural limitation of the baseline generator (documented in the main README as
an ablation control, not a quality tool), not an artefact of the ordering algorithm.

Where the strategies diverge is what happens once they reach method-level smells:

- **`seqrefactor`** reaches `BigSwitch:JSONObject.quote` first (impact-forward, GodClass
  prerequisites already attempted) and accepts it cleanly (no new smell introduced). Its next
  four steps hit `BigSwitch:JSONTokener.nextString`, which the wrapper generator turns into a
  runaway `nextStringExtracted` -> `nextStringExtractedExtracted` -> ... chain (the same pattern
  documented for the synthetic pilot subject) -- each step's prerequisites were still satisfied
  (`prerequisites_satisfied=True` throughout), so **zero cascading violations**, even though this
  particular chain does not make net progress.
- **`impact_only`** (topological constraint deliberately removed) reaches
  `LongMethod:JSONML.toString` and `MessageChains:Cookie.toString` instead -- both *method-level*
  smells whose containing class's `GodClass` resolution was only *attempted*, never actually
  accepted. Every one of its 5 accepted steps is flagged `prerequisites_satisfied=False` and
  `cascading_violation=True`: a live instance of the paper's Section IV-E worked example ("a
  detection-order plan that begins by fixing [a contained smell]... moves methods... but because
  [the containing class] still holds the responsibilities... effort is wasted"), reproduced here
  on real, unmodified production code rather than a synthetic fixture.

**Caveats, stated plainly**: this is one subject, one generator, one 12-step budget -- illustrative,
not a statistically powered claim (the formal H1-H3 paired tests in `report.hypothesis_tests`
correctly report "insufficient data" below 5 paired subjects, and this run doesn't change that).
`ordering_validity=1.0` for `seqrefactor`/`topo_only`/`unordered` reflects that every *attempted*
prerequisite was attempted before its dependents, per the existing `_prerequisites_satisfied`
accounting in `orchestrator.py` -- a rejected-but-attempted prerequisite still counts as
"satisfied" there (pre-existing behaviour, not changed by this work). Raw run reports:
`json_java_v1__<strategy>__baseline__<hash>.json`, regenerable via
`uv run seqrefactor run --config configs/opensource.yaml --out <scratch dir>` against a scratch
copy (see warning above) -- not committed here, matching `results/`/`runs/` being gitignored.

## Running the pipeline against it

**Never point `subjects_glob` at this tracked directory directly** — the orchestrator mutates its
target module in place, exactly as the main README warns for the synthetic subjects. Copy it to a
scratch location first:

```bash
cp -r datasets/opensource/json_java_v1 /tmp/scratch_json_java
uv run seqrefactor run --config configs/opensource.yaml   # subjects_glob pointed at the scratch copy
```
