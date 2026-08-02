"""Unit tests for the architectural constraint check (§5.8)."""

from __future__ import annotations

from pathlib import Path

from seqrefactor.model import Module
from seqrefactor.verify.arch import ArchCheck


def _module(tmp_path: Path, dirname: str, files: dict[str, str]) -> Module:
    root = tmp_path / dirname
    paths = []
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        paths.append(path)
    return Module(name=dirname, path=root, source_files=paths)


def test_no_changes_means_no_violations(tmp_path: Path) -> None:
    source = "package a;\npublic class Foo { public void bar() {} }\n"
    before = _module(tmp_path, "no_change_before", {"a/Foo.java": source})
    after = _module(tmp_path, "no_change_after", {"a/Foo.java": source})
    result = ArchCheck().check(before, after)
    assert result.ok is True
    assert result.violations == []


def test_removed_method_signature_is_flagged(tmp_path: Path) -> None:
    before = _module(
        tmp_path,
        "removed_before",
        {"a/Foo.java": "package a;\npublic class Foo { public void bar() {} public void baz() {} }\n"},
    )
    after = _module(
        tmp_path,
        "removed_after",
        {"a/Foo.java": "package a;\npublic class Foo { public void bar() {} }\n"},
    )
    result = ArchCheck().check(before, after)
    assert result.ok is False
    assert any("baz" in v for v in result.violations)


def test_new_circular_package_dependency_is_flagged(tmp_path: Path) -> None:
    before = _module(
        tmp_path,
        "cycle_before",
        {
            "a/A.java": "package a;\nimport b.B;\npublic class A {}\n",
            "b/B.java": "package b;\npublic class B {}\n",
        },
    )
    after = _module(
        tmp_path,
        "cycle_after",
        {
            "a/A.java": "package a;\nimport b.B;\npublic class A {}\n",
            "b/B.java": "package b;\nimport a.A;\npublic class B {}\n",
        },
    )
    result = ArchCheck().check(before, after)
    assert result.ok is False
    assert any("circular" in v for v in result.violations)
