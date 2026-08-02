"""Catalogue precedence rules (Software Specification §7.3, paper Table I).

Each rule states that a resolved instance of ``prerequisite`` must precede a
co-located instance of ``dependent`` in the smell-dependency graph. Rules are
grounded in the refactoring literature (Fowler 2018) rather than invented;
extend this table as evidence warrants, and keep the rationale honest -- it
is read by anyone auditing an edge's provenance (OR-5).
"""

from __future__ import annotations

from pydantic import BaseModel


class PrecedenceRule(BaseModel):
    id: str
    prerequisite: str
    dependent: str
    rationale: str


PRECEDENCE_RULES: list[PrecedenceRule] = [
    PrecedenceRule(
        id="R1",
        prerequisite="GodClass",
        dependent="FeatureEnvy",
        rationale="extraction relocates the envious methods",
    ),
    PrecedenceRule(
        id="R2",
        prerequisite="LargeClass",
        dependent="LongMethod",
        rationale="class split re-scopes method boundaries",
    ),
    PrecedenceRule(
        id="R3",
        prerequisite="DuplicatedCode",
        dependent="LongMethod",
        rationale="consolidation changes decomposition seams",
    ),
    PrecedenceRule(
        id="R4",
        prerequisite="DivergentChange",
        dependent="ShotgunSurgery",
        rationale="separating concerns removes the scatter",
    ),
    PrecedenceRule(
        id="R5",
        prerequisite="MessageChains",
        dependent="MiddleMan",
        rationale="shortening chains exposes idle delegation",
    ),
]


def rules_for(prerequisite_category: str, dependent_category: str) -> PrecedenceRule | None:
    """Return the catalogue rule matching an ordered (prerequisite, dependent) pair, if any."""
    for rule in PRECEDENCE_RULES:
        if rule.prerequisite == prerequisite_category and rule.dependent == dependent_category:
            return rule
    return None
