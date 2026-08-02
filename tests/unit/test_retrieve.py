"""Unit tests for retrieval (§5.6): TF-IDF vector fallback and the in-memory CPG."""

from __future__ import annotations

from pathlib import Path

from seqrefactor import ingest
from seqrefactor.retrieve.cpg import build
from seqrefactor.retrieve.retriever import Retriever
from seqrefactor.retrieve.vector import VectorRetriever
from seqrefactor.model import SmellInstance

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets" / "synthetic"


def _pilot_module():
    return ingest.load(DATASETS_DIR / "pilot_checkout_v1")


def test_vector_retriever_finds_relevant_method_in_top_k() -> None:
    # A short, term-dense method (few competing tokens) can legitimately outrank a
    # longer one under cosine-normalised TF-IDF even when the longer one is the more
    # relevant match -- normalisation penalises document length. So this asserts
    # presence within top_k, not the #1 rank, which would overclaim precision from
    # a bag-of-words fallback (see seqrefactor.retrieve.vector module docstring).
    module = _pilot_module()
    retriever = VectorRetriever(top_k=5, use_openai=False)
    chunks = retriever.retrieve("dispatchStatus switch order status", module)
    assert chunks
    assert any(c.element.endswith("dispatchStatus") for c in chunks)


def test_structural_retriever_finds_call_neighbours() -> None:
    module = _pilot_module()
    cpg = build(module)
    assert "orders.OrderService.checkout" in cpg.call_graph
    neighbours = set(cpg.call_graph.successors("orders.OrderService.checkout"))
    assert "orders.OrderService.applyDiscount" in neighbours


def test_combined_retriever_returns_both_sources() -> None:
    module = _pilot_module()
    target = SmellInstance(id="s2", category="LongMethod", loc=["orders.OrderService.checkout"])
    ctx = Retriever().context(target, module)
    sources = {c.source for c in ctx.chunks}
    assert "vector" in sources
    assert "structural" in sources
