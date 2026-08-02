"""Subprocess client for the jvm-sidecar (jvm-sidecar/README.md).

Python and the sidecar communicate only through CLI arguments and JSON files
on disk (NFR-5: Python orchestration plus a Java 17 sidecar for JVM-native
analysis and test execution). This module is the single place that knows
how to invoke the jar; seqrefactor.verify.tests and seqrefactor.verify.metrics
build on it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from seqrefactor.model import TestFailure, TestResult

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JAR = REPO_ROOT / "jvm-sidecar" / "build" / "libs" / "jvm-sidecar-all.jar"


class SidecarUnavailable(RuntimeError):
    """Raised when the jvm-sidecar jar cannot be found or Java cannot be located."""


def _jar_path() -> Path:
    override = os.environ.get("SEQREFACTOR_SIDECAR_JAR")
    jar = Path(override) if override else DEFAULT_JAR
    if not jar.is_file():
        raise SidecarUnavailable(
            f"jvm-sidecar jar not found at {jar}. Build it first: "
            "`cd jvm-sidecar && ./gradlew build` (see jvm-sidecar/README.md), "
            "or set SEQREFACTOR_SIDECAR_JAR to an existing jar."
        )
    return jar


def _java_binary() -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if candidate.is_file():
            return str(candidate)
    found = shutil.which("java")
    if found:
        return found
    raise SidecarUnavailable("No `java` executable found on PATH and JAVA_HOME is not set.")


def _invoke(args: list[str]) -> dict:
    jar = _jar_path()
    java = _java_binary()
    with tempfile.TemporaryDirectory(prefix="seqrefactor-sidecar-") as tmp:
        out_path = Path(tmp) / "result.json"
        cmd = [java, "-jar", str(jar), *args, "--out", str(out_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode not in (0,):
            raise SidecarUnavailable(
                f"sidecar exited {proc.returncode} for {cmd!r}\nstdout={proc.stdout}\nstderr={proc.stderr}"
            )
        if not out_path.is_file():
            raise SidecarUnavailable(
                f"sidecar produced no output file for {cmd!r}\nstdout={proc.stdout}\nstderr={proc.stderr}"
            )
        return json.loads(out_path.read_text(encoding="utf-8"))


def run_tests(src: Path, test_src: Path, classpath: list[Path] | None = None) -> TestResult:
    """Compile and run a module's JUnit suite via the sidecar `test` subcommand."""
    args = ["test", "--src", str(src), "--test-src", str(test_src)]
    if classpath:
        args += ["--classpath", os.pathsep.join(str(p) for p in classpath)]
    payload = _invoke(args)
    return TestResult(
        success=payload["success"],
        tests_run=payload["tests_run"],
        tests_passed=payload["tests_passed"],
        tests_failed=payload["tests_failed"],
        failures=[TestFailure(**f) for f in payload.get("failures", [])],
        compile_errors=list(payload.get("compile_errors", [])),
    )


def run_metrics(src: Path) -> list[dict]:
    """Run CK object-oriented metrics via the sidecar `metrics` subcommand.

    Returns the raw list of per-class metric dicts (class, cbo, lcom, wmc, rfc, loc);
    seqrefactor.verify.metrics maps these onto module elements for the five-family facade.
    """
    payload = _invoke(["metrics", "--src", str(src)])
    return list(payload.get("classes", []))


def is_available() -> bool:
    try:
        _jar_path()
        _java_binary()
    except SidecarUnavailable:
        return False
    return True
