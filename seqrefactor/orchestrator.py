"""Orchestrator: the stateful S1..S7 pipeline (Software Specification §3.1, §5.10).

The control flow below is implemented as plain, directly-testable Python
(`Orchestrator._run_step`, `_select_ordering`, ...); `build_graph` wraps the
same methods as LangGraph nodes so the documented S1..S7 staged architecture
is genuinely what executes, while the business logic itself stays unit
testable without spinning up the graph runtime.

DESIGN DECISION -- the loop is the point (§3.1): every iteration re-detects
smells, rebuilds the dependency graph, and recomputes the agenda from
scratch over whatever is still unresolved (OR-4), then acts on only the
single highest-priority actionable item before looping. This is a strict
superset of "rebuild after every ACCEPTED step" -- rebuilding on every
iteration (including after a reject) is simpler to implement correctly and
never less safe, only more conservative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from seqrefactor import ingest
from seqrefactor._worktree import isolated_copy
from seqrefactor.detect import native as detect_native
from seqrefactor.gate import Gate
from seqrefactor.generate import baseline as gen_baseline
from seqrefactor.generate import llm as gen_llm
from seqrefactor.graph import builder as graph_builder
from seqrefactor.model import (
    Config,
    Evidence,
    GeneratorName,
    Module,
    Ordering,
    RunReport,
    SmellDependencyGraph,
    SmellId,
    SmellInstance,
    StepRecord,
    Strategy,
    Verdict,
)
from seqrefactor.order import impact as impact_scorer
from seqrefactor.order import orderer
from seqrefactor.retrieve.retriever import Retriever
from seqrefactor.verify.arch import ArchCheck
from seqrefactor.verify.metrics import MetricFacade
from seqrefactor.verify.tests import SidecarTestRunner


def _select_ordering(
    strategy: Strategy, g: SmellDependencyGraph, impact_scores: dict[SmellId, float]
) -> Ordering:
    """The four ablation arms (§8.3 Variables): only the ordering strategy varies;
    everything else in the loop is identical across arms so the comparison isolates
    ordering effects from generation effects."""
    if strategy == "unordered":
        return Ordering(agenda=[n.id for n in g.nodes], escalations=[])
    if strategy == "impact_only":
        # Best-first by impact with the topological constraint deliberately removed.
        agenda = sorted((n.id for n in g.nodes), key=lambda sid: -impact_scores[sid])
        return Ordering(agenda=agenda, escalations=[])
    if strategy == "topo_only":
        # A valid linear extension with arbitrary (non-impact) priority: flat impact
        # makes the priority-queue Kahn traversal degrade to a deterministic
        # id-tie-broken topological sort while keeping OR-1 safety intact.
        flat = dict.fromkeys(impact_scores, 0.0)
        return orderer.order(g, flat)
    return orderer.order(g, impact_scores)  # "seqrefactor"


def _prerequisites_satisfied(target_id: SmellId, g: SmellDependencyGraph, resolved: set[SmellId]) -> bool:
    """True if every prerequisite of ``target_id`` still present in ``g`` (i.e. not yet
    resolved) is empty -- used to flag cascading violations on unsafe ablation arms."""
    prerequisites = {e.src for e in g.edges if e.dst == target_id}
    return prerequisites.issubset(resolved)


class _PipelineState(TypedDict):
    module: Module
    cfg: Config
    strategy: Strategy
    generator_name: GeneratorName
    resolved: set[SmellId]
    steps: list[StepRecord]
    step_index: int
    escalations: list[list[SmellId]]
    max_steps: int
    done: bool


class Orchestrator:
    def __init__(self) -> None:
        self.retriever = Retriever()
        self.metric_facade = MetricFacade()
        self.test_runner = SidecarTestRunner()
        self.arch_check = ArchCheck()
        self.gate = Gate()
        self._graph = self._build_graph()

    # -- LangGraph wiring (§3.1): a single "iterate" node that performs one
    # S1(detect)..S7(gate) pass over the current state, looping back on itself
    # until the agenda is exhausted or every remaining smell is escalated.
    def _build_graph(self):
        graph = StateGraph(_PipelineState)
        graph.add_node("iterate", self._iterate)
        graph.set_entry_point("iterate")
        graph.add_conditional_edges(
            "iterate", lambda state: END if state["done"] else "iterate"
        )
        return graph.compile()

    def _iterate(self, state: _PipelineState) -> dict[str, Any]:
        module = state["module"]
        cfg = state["cfg"]
        strategy = state["strategy"]
        resolved = state["resolved"]
        step_index = state["step_index"]

        if step_index >= state["max_steps"]:
            return {"done": True}

        # S1 Detect + S2 Build
        smells = detect_native.detect(module)
        current_ids = {s.id for s in smells}
        pending = [s for s in smells if s.id not in resolved]
        if not pending:
            return {"done": True}

        g = graph_builder.build(pending, module)

        # S3 Order (THE CONTRIBUTION for strategy == "seqrefactor")
        impact_scores = impact_scorer.score(g, cfg.impact_weights)
        ordering = _select_ordering(strategy, g, impact_scores)

        escalated_ids = {sid for comp in ordering.escalations for sid in comp}
        actionable = [sid for sid in ordering.agenda if sid not in escalated_ids]
        if not actionable:
            return {"escalations": ordering.escalations, "done": True}  # OR-3

        target_id = actionable[0]
        target = next(s for s in pending if s.id == target_id)
        prerequisites_satisfied = _prerequisites_satisfied(target_id, g, resolved)

        # S4 Retrieve + S5 Generate
        ctx = self.retriever.context(target, module)
        candidate = self._generate(state["generator_name"], target, ctx, module, cfg.seed + step_index)

        # S6 Verify + S7 Gate (+ re-detect on accept, folded into _evaluate)
        verdict, module = self._evaluate(module, target, candidate)

        introduced: list[SmellId] = []
        if verdict.accepted:
            after_ids = {s.id for s in detect_native.detect(module)}
            introduced = sorted(after_ids - current_ids)

        step = StepRecord(
            index=step_index,
            smell=target_id,
            verdict=verdict,
            introduced=introduced,
            # Per the paper's Definition (cascading violation): a step introduces a smell
            # that would not have arisen had every prerequisite of the target been
            # resolved first.
            cascading_violation=bool(introduced) and not prerequisites_satisfied,
            prerequisites_satisfied=prerequisites_satisfied,
        )

        new_resolved = set(resolved)
        new_resolved.add(target_id)  # handled either way: accepted, or rejected-and-not-retried

        return {
            "module": module,
            "resolved": new_resolved,
            "steps": [*state["steps"], step],
            "step_index": step_index + 1,
            "escalations": ordering.escalations,
            "done": False,
        }

    # -- S5 Generate --------------------------------------------------------
    def _generate(self, generator_name: GeneratorName, target: SmellInstance, ctx, module: Module, seed: int):
        if generator_name == "llm":
            return gen_llm.refactor(target, ctx, module, seed=seed)
        return gen_baseline.refactor(target, ctx, module, seed=seed)

    # -- S6 Verify + S7 Gate, inside an isolated worktree (NFR-1) ------------
    def _evaluate(
        self, module: Module, target: SmellInstance, candidate
    ) -> tuple[Verdict, Module]:
        from seqrefactor import _treesitter as ts

        if not candidate.patch:
            verdict = Verdict(smell=target.id, accepted=False, rationale="generator produced no patch")
            return verdict, module

        element = target.loc[0] if target.loc else target.category
        real_file = ts.locate_file(element, module.source_files)
        if real_file is None:
            verdict = Verdict(
                smell=target.id, accepted=False, rationale=f"could not locate source file for {element}"
            )
            return verdict, module

        relative_file = real_file.relative_to(module.path)

        with isolated_copy(module.path) as candidate_root:
            candidate_file = candidate_root / relative_file
            candidate_file.write_text(candidate.patch, encoding="utf-8")
            candidate_module = ingest.load(candidate_root)

            test_result = self.test_runner.run(candidate_module)
            metric_delta = self.metric_facade.deltas(module, candidate_module, target.loc)
            arch_result = self.arch_check.check(module, candidate_module)

            evidence = Evidence(
                metric=metric_delta, tests_pass=test_result.success, arch_ok=arch_result.ok
            )
            verdict = self.gate.decide(target.id, evidence)

            if verdict.accepted:
                real_file.write_text(candidate.patch, encoding="utf-8")

        if verdict.accepted:
            return verdict, ingest.load(module.path, classpath=module.classpath)
        return verdict, module

    # -- The full re-planning loop (S1..S7, FR-11, OR-4) ---------------------
    def run_one(
        self,
        path: Path,
        cfg: Config,
        strategy: Strategy | None = None,
        generator: GeneratorName | None = None,
        max_steps: int | None = None,
    ) -> RunReport:
        strategy = strategy or cfg.strategies[0]
        generator_name: GeneratorName = generator or cfg.generators[0]
        max_steps = max_steps if max_steps is not None else cfg.max_steps

        module = ingest.load(Path(path))
        precondition = ingest.check_preconditions(module, coverage_min=cfg.coverage_min)
        if not precondition.passed:
            return RunReport(subject=module.name, strategy=strategy, generator=generator_name)

        initial_state: _PipelineState = {
            "module": module,
            "cfg": cfg,
            "strategy": strategy,
            "generator_name": generator_name,
            "resolved": set(),
            "steps": [],
            "step_index": 0,
            "escalations": [],
            "max_steps": max_steps,
            "done": False,
        }
        final_state = self._graph.invoke(
            initial_state, config={"recursion_limit": max_steps + 10}
        )

        return RunReport(
            subject=final_state["module"].name,
            strategy=strategy,
            generator=generator_name,
            steps=final_state["steps"],
            escalations=final_state["escalations"],
        )

    def run_matrix(self, cfg: Config, subject_paths: list[Path]) -> list[RunReport]:
        return [
            self.run_one(path, cfg, strategy=strategy, generator=generator)
            for path in subject_paths
            for strategy in cfg.strategies
            for generator in cfg.generators
        ]
