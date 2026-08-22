"""Catalogue precedence rules (Software Specification §7.3, paper Table I).

Each rule states that a resolved instance of ``prerequisite`` must precede a
co-located instance of ``dependent`` in the smell-dependency graph. Rules are
grounded in the refactoring literature (Fowler 2018) rather than invented;
extend this table as evidence warrants, and keep the rationale honest -- it
is read by anyone auditing an edge's provenance (OR-5).
"""

from __future__ import annotations

from typing import Literal

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


# --------------------------------------------------------------------------
# Signed (positive/negative) dependency table (Working Brief §2 / C1)
# --------------------------------------------------------------------------
#
# HONESTY NOTE: the Working Brief that requested this table asks for
# probabilities "seeded from the operation-frequency ratings" of a Markovic
# analysis cited as [32] in the paper. That citation does not exist in this
# repository's paper draft (SEQ_REFACTOR_paper.docx, references end at
# [31]) -- see REPO_MAP.md §3 for the full discrepancy this was flagged
# against. Rather than fabricate a citation or invent numbers and present
# them as literature-derived, every probability below is an illustrative
# default seeded by directional plausibility from the same refactoring
# literature the PREREQUISITE rules above cite (Fowler 2018), with its
# rationale stated inline. These are placeholders for a future increment
# that mines real co-occurrence/cascade frequencies from version history
# (paper Section IX-D's own stated future work), not a claim of measured
# frequency. Category pairs here are deliberately disjoint from
# PRECEDENCE_RULES above: a given ordered category pair is either a hard
# prerequisite or a soft signed dependency, never both, so no edge is ever
# contradictorily typed.


class SignedDependencyRule(BaseModel):
    id: str
    polarity: Literal["positive", "negative"]
    source: str  # the category whose resolution is the trigger
    target: str  # the category whose likelihood of co-resolution/cascade is affected
    probability: float  # in [0, 1], illustrative default (see HONESTY NOTE above)
    operation: str  # the refactoring operation that induces this relation
    rationale: str


SIGNED_DEPENDENCY_RULES: list[SignedDependencyRule] = [
    SignedDependencyRule(
        id="P1",
        polarity="positive",
        source="LongMethod",
        target="FeatureEnvy",
        probability=0.55,
        operation="Extract Method",
        rationale="extracting a long method's cohesive fragments frequently relocates "
        "the same data-hungry code that also drives feature envy, so resolving the "
        "former often resolves or shrinks the latter as a side effect",
    ),
    SignedDependencyRule(
        id="P2",
        polarity="positive",
        source="BigSwitch",
        target="DuplicatedCode",
        probability=0.5,
        operation="Replace Conditional with Polymorphism",
        rationale="switch branches over a type code are a common site of near-duplicate "
        "per-case logic, so polymorphic replacement tends to consolidate that "
        "duplication as part of the same transformation",
    ),
    SignedDependencyRule(
        id="P3",
        polarity="positive",
        source="DivergentChange",
        target="LargeClass",
        probability=0.6,
        operation="Extract Class",
        rationale="separating the unrelated reasons a class changes (divergent change) "
        "is the same extraction that shrinks an oversized class, so the two "
        "co-resolve under a single Extract Class operation",
    ),
    SignedDependencyRule(
        id="N1",
        polarity="negative",
        source="FeatureEnvy",
        target="ShotgunSurgery",
        probability=0.35,
        operation="Move Method",
        rationale="moving an envious method to the class it favours can scatter its "
        "remaining call sites across the callers left behind, cascading into "
        "shotgun surgery if those callers are not addressed in the same pass",
    ),
    SignedDependencyRule(
        id="N2",
        polarity="negative",
        source="GodClass",
        target="DivergentChange",
        probability=0.3,
        operation="Extract Class",
        rationale="splitting a god class along the wrong seam can leave each resulting "
        "class responsible for more than one reason to change, reintroducing "
        "divergent change at smaller scale",
    ),
    SignedDependencyRule(
        id="N3",
        polarity="negative",
        source="LargeClass",
        target="MessageChains",
        probability=0.4,
        operation="Extract Class",
        rationale="splitting a large class into collaborating parts can lengthen the "
        "navigation path between them, growing message chains that did not "
        "exist while the responsibilities were still colocated",
    ),
]


def signed_rule_for(source_category: str, target_category: str) -> SignedDependencyRule | None:
    """Return the signed (positive/negative) catalogue rule for an ordered category
    pair, if any. Disjoint from ``rules_for`` by construction (see module docstring)."""
    for rule in SIGNED_DEPENDENCY_RULES:
        if rule.source == source_category and rule.target == target_category:
            return rule
    return None
