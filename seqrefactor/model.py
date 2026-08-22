"""Pydantic data model shared by every pipeline stage (Software Specification §6).

Stages communicate only through these types, never through side channels, so
any stage can be tested in isolation with recorded fixtures. Derived
quantities (net smell resolution, cascading-violation counts, ordering
validity) are computed properties over :class:`RunReport`, never stored as
independent fields, so a reported number is always re-derivable from the
persisted per-step artefacts (NFR-3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, computed_field

EdgePolarity = Literal["prerequisite", "positive", "negative"]

SmellId = str
LocSet = list[str]

# --------------------------------------------------------------------------
# Ingest
# --------------------------------------------------------------------------


class Module(BaseModel):
    """A Java module under refactoring: its code units and test-suite handle."""

    name: str
    path: Path
    source_files: list[Path] = Field(default_factory=list)
    test_files: list[Path] = Field(default_factory=list)
    main_dir: Path | None = None  # source root passed to the sidecar's --src
    test_dir: Path | None = None  # test root passed to the sidecar's --test-src
    classpath: list[Path] = Field(default_factory=list)
    coverage: float | None = None


class PreconditionReport(BaseModel):
    coverage: float
    coverage_min: float
    passed: bool
    reasons: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Detection and the smell-dependency graph (§6, §7.3)
# --------------------------------------------------------------------------


class SmellInstance(BaseModel):
    id: SmellId
    category: str  # 'GodClass' | 'LongMethod' | 'FeatureEnvy' | ...
    loc: LocSet = Field(default_factory=list)
    severity: float = 1.0


class DepEdge(BaseModel):
    """A directed smell-dependency edge, typed by polarity (Working Brief §2 / C1).

    PREREQUISITE edges are hard: they are the only edges the ordering algorithm's
    feasibility check (indegree/topological constraint) honours (see
    ``order/orderer.py``). POSITIVE (co-resolution) and NEGATIVE (cascading) edges
    are soft: they never gate feasibility, only impact tie-breaking and cascade
    anticipation among smells that are already eligible.
    """

    src: SmellId  # prerequisite / source of the (co-)relation
    dst: SmellId  # dependent (resolve after src, for PREREQUISITE edges)
    provenance: str  # rule id, or the shared elements that induced it
    polarity: EdgePolarity = "prerequisite"
    probability: float = 1.0  # in [0, 1]; 1.0 for hard PREREQUISITE edges by construction
    inducing_operation: str | None = None  # the refactoring operation that induces this relation


class SmellDependencyGraph(BaseModel):
    nodes: list[SmellInstance] = Field(default_factory=list)
    edges: list[DepEdge] = Field(default_factory=list)

    def node_ids(self) -> set[SmellId]:
        return {n.id for n in self.nodes}


# --------------------------------------------------------------------------
# Impact scoring and ordering (§7.1, §7.2, Eq. 1-4)
# --------------------------------------------------------------------------


class ImpactWeights(BaseModel):
    alpha: float = 0.4  # coupling
    beta: float = 0.4  # complexity
    gamma: float = 0.2  # co-occurrence


class OperationCounters(BaseModel):
    """Per-run operation tallies for complexity instrumentation (Working Brief §4 /
    RQ6, H5). Populated by ``order/orderer.py`` and ``graph/incremental.py`` so the
    empirical scaling study is read from real counters, never hand-entered.
    """

    vertex_touches: int = 0
    edge_touches: int = 0
    heap_operations: int = 0
    order_renumbering_operations: int = 0

    def __add__(self, other: OperationCounters) -> OperationCounters:
        return OperationCounters(
            vertex_touches=self.vertex_touches + other.vertex_touches,
            edge_touches=self.edge_touches + other.edge_touches,
            heap_operations=self.heap_operations + other.heap_operations,
            order_renumbering_operations=self.order_renumbering_operations
            + other.order_renumbering_operations,
        )


class Ordering(BaseModel):
    agenda: list[SmellId] = Field(default_factory=list)  # dependency-safe, impact-forward
    escalations: list[list[SmellId]] = Field(default_factory=list)  # SCCs, human review
    counters: OperationCounters = Field(default_factory=OperationCounters)


# --------------------------------------------------------------------------
# Retrieval and generation
# --------------------------------------------------------------------------


class RetrievedChunk(BaseModel):
    source: Literal["vector", "structural"]
    element: str
    text: str
    score: float = 0.0


class GenContext(BaseModel):
    target: SmellId
    chunks: list[RetrievedChunk] = Field(default_factory=list)


class Candidate(BaseModel):
    smell: SmellId
    generator: str
    patch: str
    raw_output: str
    seed: int
    worktree: Path | None = None


# --------------------------------------------------------------------------
# Verification (§5.8, five-family metric delta + tests + architecture)
# --------------------------------------------------------------------------


class MetricDelta(BaseModel):
    cohesion: float = 0.0
    coupling: float = 0.0
    complexity: float = 0.0
    readability: float = 0.0
    architecture: float = 0.0


class TestFailure(BaseModel):
    test: str
    message: str


class TestResult(BaseModel):
    success: bool
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    failures: list[TestFailure] = Field(default_factory=list)
    compile_errors: list[str] = Field(default_factory=list)


class ArchResult(BaseModel):
    ok: bool
    violations: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    metric: MetricDelta
    tests_pass: bool
    arch_ok: bool


class Verdict(BaseModel):
    smell: SmellId
    accepted: bool
    rationale: str


# --------------------------------------------------------------------------
# Run reporting (§9, §11, cascading-violation and NSR accounting)
# --------------------------------------------------------------------------


class StepRecord(BaseModel):
    index: int
    smell: SmellId
    verdict: Verdict
    introduced: list[SmellId] = Field(default_factory=list)  # new smells after this step
    cascading_violation: bool = False  # per the paper's Definition (cascading violation)
    prerequisites_satisfied: bool = True  # feeds ordering-validity (OR-1 audit)


class RunReport(BaseModel):
    subject: str
    strategy: str
    generator: str
    steps: list[StepRecord] = Field(default_factory=list)
    escalations: list[list[SmellId]] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def net_smell_resolution(self) -> int:
        """NSR = |R| - |I| (Eq. 4): accepted resolutions minus introduced smells."""
        resolved = sum(1 for s in self.steps if s.verdict.accepted)
        introduced = sum(len(s.introduced) for s in self.steps)
        return resolved - introduced

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cascading_violations(self) -> int:
        return sum(1 for s in self.steps if s.cascading_violation)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ordering_validity(self) -> float:
        """Fraction of steps whose prerequisites were satisfied when executed."""
        if not self.steps:
            return 1.0
        satisfied = sum(1 for s in self.steps if s.prerequisites_satisfied)
        return satisfied / len(self.steps)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def escalation_rate(self) -> float:
        escalated = sum(len(c) for c in self.escalations)
        total = escalated + len(self.steps)
        return escalated / total if total else 0.0


# --------------------------------------------------------------------------
# Complexity instrumentation (Working Brief §4 / C2, C6; RQ6, H5)
# --------------------------------------------------------------------------


class ComplexityRecord(BaseModel):
    """One measured maintenance step, incremental or from-scratch (Working Brief §4).

    ``wall_clock_seconds`` is the median of repeated runs at the call site
    (``eval/complexity.py``), never a single sample, so timing noise does not leak
    into the scaling study.
    """

    subject: str
    step_index: int
    strategy: Literal["incremental", "from_scratch"]
    module_size: int  # |V| of the graph at this step, for the scaling study's x-axis
    counters: OperationCounters
    wall_clock_seconds: float


# --------------------------------------------------------------------------
# Dependency-mass study (Working Brief §5 / C7; RQ5, H4)
# --------------------------------------------------------------------------


class DependencyMass(BaseModel):
    """Weighted positive/negative dependency mass for one subject (Working Brief §5).

    HONESTY NOTE (carried from the brief verbatim): the dependency probabilities
    behind this mass are seeded from the catalogue (``graph/rules.py``), not mined
    from version histories, so this measures a modelled distribution, not an
    observed one. Mining probabilities from real refactoring history is future
    work; see the catalogue module's own docstring for the same note at the
    source of the numbers.
    """

    subject: str
    positive_mass: float  # sum of probability over POSITIVE edges
    negative_mass: float  # sum of probability over NEGATIVE edges
    co_resolution_events: int  # realised: both endpoints of a POSITIVE edge resolved
    cascading_violation_events: int  # realised: a NEGATIVE edge's cascade was observed

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mass_ratio(self) -> float:
        """negative_mass / positive_mass; undefined (returns 0.0) when positive_mass is 0."""
        return self.negative_mass / self.positive_mass if self.positive_mass else 0.0


# --------------------------------------------------------------------------
# Configuration (drives Orchestrator.run_one / run_matrix, §8.3)
# --------------------------------------------------------------------------

Strategy = Literal["seqrefactor", "impact_only", "topo_only", "unordered"]
GeneratorName = Literal["llm", "baseline"]


class WeightSweep(BaseModel):
    alpha: list[float] = Field(default_factory=list)
    beta: list[float] = Field(default_factory=list)


class Config(BaseModel):
    subjects_glob: str
    strategies: list[Strategy] = Field(default_factory=lambda: ["seqrefactor"])
    generators: list[GeneratorName] = Field(default_factory=lambda: ["baseline"])
    impact_weights: ImpactWeights = Field(default_factory=ImpactWeights)
    discount: float = 0.9
    coverage_min: float = 0.80
    seed: int = 20260101
    weight_sweep: WeightSweep | None = None
