"""JUnit test execution (Software Specification §5.8) via the jvm-sidecar.

A thin wrapper: all compilation and JUnit Platform Launcher work happens in
jvm-sidecar (see jvm-sidecar/README.md); this module only shapes the call
and surfaces a clear error when a module has no discoverable test root.
"""

from __future__ import annotations

from seqrefactor import _sidecar
from seqrefactor.model import Module, TestResult


class NoTestRootError(RuntimeError):
    pass


class SidecarTestRunner:
    """Implements the ``TestRunner`` contract (§5.8): ``run(module) -> TestResult``."""

    def run(self, module: Module) -> TestResult:
        if module.main_dir is None or module.test_dir is None:
            raise NoTestRootError(
                f"module {module.name!r} has no main_dir/test_dir "
                "(load it with seqrefactor.ingest.load, which populates both)"
            )
        return _sidecar.run_tests(module.main_dir, module.test_dir, module.classpath)
