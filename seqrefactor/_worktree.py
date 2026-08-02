"""Isolated candidate evaluation (NFR-1: "each candidate is evaluated in a fresh
git worktree; rollback discards the worktree. No shared mutable state between
candidates").

IMPLEMENTATION NOTE: NFR-1's text names `git worktree` specifically. This
module instead copies the module directory into a fresh temporary directory
per candidate. The isolation guarantee NFR-1 is actually after -- a fresh,
disposable copy per candidate, with a rejected candidate never touching the
caller's working copy, and no state leaking between candidates evaluated one
after another -- holds either way. A literal `git worktree add ... HEAD`
was tried first and rejected: it only ever sees what is committed, so it
silently evaluates a stale (or, for an uncommitted new module, entirely
missing) tree whenever the subject has local changes -- exactly the
common case while a subject module is still being developed. A
git-worktree-backed variant is a reasonable alternative for a workflow
where every subject module is fully committed before a run; swapping the
one function below is all that would take.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def isolated_copy(module_path: Path) -> Iterator[Path]:
    """Yield a path to an isolated copy of ``module_path`` for the caller to mutate
    and verify; the copy is discarded on exit regardless of what the caller decided."""
    module_path = Path(module_path).resolve()
    tmp_dir = Path(tempfile.mkdtemp(prefix="seqrefactor-eval-"))
    dest = tmp_dir / module_path.name
    shutil.copytree(module_path, dest)
    try:
        yield dest
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
