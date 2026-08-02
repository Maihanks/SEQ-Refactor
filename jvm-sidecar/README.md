# jvm-sidecar

A small Gradle/Java 17 CLI that the SEQ-Refactor Python orchestrator shells out to for
two tasks it cannot do itself on the JVM side:

1. Compiling and running a Java module's JUnit 5 test suite (`test` subcommand).
2. Computing CK object-oriented metrics (CBO, LCOM, WMC, RFC, LOC) for a Java module
   (`metrics` subcommand).

Python and this sidecar communicate only through CLI arguments and JSON files on disk;
there is no other coupling.

## Prerequisites

- JDK 17 or newer on `PATH`, or `JAVA_HOME` pointing at one.
- No local Gradle install is required — use the checked-in wrapper (`gradlew` /
  `gradlew.bat`).

## Building

From inside `jvm-sidecar/`:

```bash
./gradlew build        # Linux/macOS
gradlew.bat build       # Windows
```

This compiles the main and test sources, runs the sidecar's own JUnit test suite, and
produces a runnable fat jar via the Shadow plugin at:

```
jvm-sidecar/build/libs/jvm-sidecar-all.jar
```

(`jvm-sidecar` is the Gradle project name from `settings.gradle`; `-all` is the
classifier configured for the shadow jar. Verify the exact name with
`ls build/libs/` after a build — the plugin/version combination determines it.)

## Running the subcommands

Both subcommands are invoked through the fat jar, e.g. `java -jar build/libs/jvm-sidecar-all.jar <subcommand> [options]`.

### `metrics` — CK object-oriented metrics

```bash
java -jar build/libs/jvm-sidecar-all.jar metrics \
  --src path/to/Module/src/main/java \
  --out metrics.json
```

Arguments:

- `--src <dir>` — source root to analyze. May contain one or many `.java` files/classes.
- `--out <path.json>` — where to write the result JSON.

Output JSON shape:

```json
{
  "classes": [
    {"class": "com.example.Foo", "cbo": 3, "lcom": 2, "wmc": 7, "rfc": 5, "loc": 42}
  ]
}
```

One object per analyzed class. The fields map directly onto CK 0.6.4's
`CKClassResult` getters: `class` <- `getClassName()`, `cbo` <- `getCbo()`,
`lcom` <- `getLcom()`, `wmc` <- `getWmc()`, `rfc` <- `getRfc()`, `loc` <- `getLoc()`.
CK is invoked as `new CK().calculate(srcPathString, notifier)`, where `notifier` is a
`CKNotifier` callback (`void notify(CKClassResult result)`) collecting one result per
class — this matches CK's actual 0.6.4 API as verified against the resolved jar's
class files (`javap`), not just its docs.

### `test` — compile and run a module's JUnit 5 suite

```bash
java -jar build/libs/jvm-sidecar-all.jar test \
  --src path/to/Module/src/main/java \
  --test-src path/to/Module/src/test/java \
  --out result.json
```

Arguments:

- `--src <dir>` — main source root of the module under test.
- `--test-src <dir>` — test source root of the module under test.
- `--classpath <paths>` — optional, OS-path-separator-joined extra jars/dirs for the
  target module's own dependencies (JUnit itself does not need to be listed here; it is
  already on the sidecar's own runtime classpath and is reused for compiling and running
  the target module's tests).
- `--out <path.json>` — where to write the result JSON.

Behavior: every `.java` file under `--src` and `--test-src` is compiled together, in an
isolated temporary output directory, using `javax.tools.ToolProvider.getSystemJavaCompiler()`
with a classpath made of the sidecar's own runtime classpath plus anything passed via
`--classpath`. If compilation fails, the diagnostics are captured into `compile_errors`
and no tests are run. Otherwise the compiled tests are executed with the JUnit Platform
Launcher API (`selectClasspathRoots` against the temp output directory, since that was
simpler and more reliable than package-based selection for a location the sidecar's own
classloader doesn't already know about), using a `SummaryGeneratingListener` to collect
results.

Output JSON shape:

```json
{
  "success": true,
  "tests_run": 5,
  "tests_passed": 4,
  "tests_failed": 1,
  "failures": [
    {"test": "com.example.FooTest#barWorks", "message": "expected: <1> but was: <2>"}
  ],
  "compile_errors": []
}
```

`success` is `true` iff `compile_errors` is empty AND `tests_failed == 0`.

**Exit codes are not the success signal.** The process exits `0` for any well-formed
result, including a failing test suite or a compile error — those are normal,
expected outcomes for a verification gate to consume, carried in the JSON `success`
field, not sidecar failures. The process exits `1` only on a genuine sidecar-internal
error (e.g. it could not write the output file at all), and `2` if the subcommand
itself is missing or unrecognized (prints a usage message to stderr).

## Integration point

This sidecar is invoked as a subprocess by the Python orchestrator's
`seqrefactor/verify/tests.py` (JUnit runner, via the `test` subcommand) and
`seqrefactor/verify/metrics.py` / `seqrefactor/order/impact.py` (CK metrics, via the
`metrics` subcommand). Those Python files may not exist yet at the time this README was
written — this section documents the intended integration point by name, not a
guarantee those files are present.

## Project layout

```
jvm-sidecar/
  build.gradle
  settings.gradle
  gradlew, gradlew.bat, gradle/wrapper/   (checked-in Gradle wrapper)
  src/main/java/org/seqrefactor/sidecar/
    SidecarCli.java          entry point, dispatches to the two subcommands
    CliArgs.java              tiny --flag value argument parser
    TestRunnerCommand.java    `test` subcommand: compile + JUnit Platform Launcher
    MetricsCommand.java       `metrics` subcommand: CK integration
    TestRunResult.java        JSON result model for `test`
    MetricsResult.java        JSON result model for `metrics`
  src/test/java/org/seqrefactor/sidecar/
    TestRunnerCommandTest.java   pass/fail counting + compile-error handling
    MetricsCommandTest.java     CK metrics on a small fixture class
```
