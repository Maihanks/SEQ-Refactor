"""Unit tests for the native tree-sitter SmellDetector (§5.2, §9.1)."""

from __future__ import annotations

from pathlib import Path

from seqrefactor.detect.native import detect
from seqrefactor.model import Module


def _module_from(tmp_path: Path, java_source: str, name: str = "Fixture") -> Module:
    path = tmp_path / f"{name}.java"
    path.write_text(java_source, encoding="utf-8")
    return Module(name=name, path=tmp_path, source_files=[path])


def test_plain_data_class_is_not_flagged_as_god_class(tmp_path: Path) -> None:
    source = """
    package fixtures;
    public class Point {
        private final int x;
        private final int y;
        public Point(int x, int y) { this.x = x; this.y = y; }
        public int getX() { return x; }
        public int getY() { return y; }
        public void setX(int x) { this.x = x; }
        public void setY(int y) { this.y = y; }
        public int getSum() { return x; }
        public int getDiff() { return y; }
    }
    """
    module = _module_from(tmp_path, source, "Point")
    smells = detect(module)
    assert not any(s.category == "GodClass" for s in smells)


def test_wide_switch_is_flagged_as_big_switch(tmp_path: Path) -> None:
    source = """
    package fixtures;
    public class Dispatcher {
        public String route(String status) {
            switch (status) {
                case "A": return "1";
                case "B": return "2";
                case "C": return "3";
                case "D": return "4";
                default: return "0";
            }
        }
    }
    """
    module = _module_from(tmp_path, source, "Dispatcher")
    smells = detect(module)
    big_switches = [s for s in smells if s.category == "BigSwitch"]
    assert len(big_switches) == 1
    assert big_switches[0].loc == ["fixtures.Dispatcher.route"]


def test_long_receiver_chain_is_flagged_as_message_chain(tmp_path: Path) -> None:
    source = """
    package fixtures;
    public class Chainy {
        public String go(A a) {
            return a.getB().getC().getD().name();
        }
    }
    """
    module = _module_from(tmp_path, source, "Chainy")
    smells = detect(module)
    assert any(s.category == "MessageChains" for s in smells)


def test_pilot_checkout_module_flags_god_class_and_its_methods() -> None:
    src_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "datasets"
        / "synthetic"
        / "pilot_checkout_v1"
        / "src"
        / "main"
        / "java"
    )
    files = list(src_dir.rglob("*.java"))
    module = Module(name="pilot_checkout_v1", path=src_dir, source_files=files)

    smells = detect(module)
    categories = {s.category for s in smells}

    god_classes = [s for s in smells if s.category == "GodClass"]
    assert god_classes and god_classes[0].loc == ["orders.OrderService"]
    assert "BigSwitch" in categories
    assert "LongMethod" in categories or "MessageChains" in categories
