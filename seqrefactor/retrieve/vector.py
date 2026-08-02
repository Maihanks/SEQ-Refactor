"""Vector (semantic) retrieval (Software Specification §5.6, §3.2).

Chunks each method in the module and ranks chunks by similarity to the
target smell's own code. Uses OpenAI embeddings when ``OPENAI_API_KEY`` is
configured (see .env.example); otherwise falls back to a dependency-free
TF-IDF cosine similarity so retrieval works offline and in CI with no
external service -- consistent with the spec's own HONESTY NOTE: "a graph
database is optional at pilot scale... frameworks earn their place only
when a measured need appears." The same reasoning applies here to a full
vector-store dependency.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter

from seqrefactor import _treesitter as ts
from seqrefactor.model import Module, RetrievedChunk

_TOKEN_SPLIT = "()[]{};.,\"'\n\t "
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _split_camel_case(word: str) -> list[str]:
    """`dispatchStatus` -> `["dispatch", "status"]`. Standard for code-search
    tokenization: identifiers carry their real information in subwords, and a
    query term like "status" should match both `dispatchStatus` and `getStatus`."""
    return [part.lower() for part in _CAMEL_BOUNDARY_RE.split(word) if part]


def _tokenize(text: str) -> list[str]:
    for ch in _TOKEN_SPLIT:
        text = text.replace(ch, " ")
    tokens: list[str] = []
    for raw in text.split():
        if len(raw) <= 1:
            continue
        tokens.append(raw.lower())
        tokens.extend(_split_camel_case(raw))
    return tokens


def _chunks(module: Module) -> list[tuple[str, str]]:
    """One (element_name, source_snippet) pair per method in the module."""
    out: list[tuple[str, str]] = []
    for source_file in module.source_files:
        text = source_file.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for cls in ts.parse_file(source_file):
            for method in cls.methods:
                snippet = "\n".join(lines[method.start_line - 1 : method.end_line])
                out.append((method.qualified_name, snippet))
    return out


def _tfidf_rank(query: str, chunks: list[tuple[str, str]], top_k: int) -> list[RetrievedChunk]:
    query_tokens = Counter(_tokenize(query))
    doc_tokens = [Counter(_tokenize(text)) for _, text in chunks]

    doc_freq: Counter[str] = Counter()
    for tokens in doc_tokens:
        doc_freq.update(tokens.keys())
    n_docs = max(1, len(chunks))

    def vectorise(tokens: Counter[str]) -> dict[str, float]:
        return {
            term: count * math.log(1 + n_docs / (1 + doc_freq.get(term, 0)))
            for term, count in tokens.items()
        }

    query_vec = vectorise(query_tokens)
    scored: list[tuple[float, str, str]] = []
    for (element, text), tokens in zip(chunks, doc_tokens):
        doc_vec = vectorise(tokens)
        dot = sum(query_vec.get(t, 0.0) * w for t, w in doc_vec.items())
        norm_q = math.sqrt(sum(w * w for w in query_vec.values())) or 1.0
        norm_d = math.sqrt(sum(w * w for w in doc_vec.values())) or 1.0
        similarity = dot / (norm_q * norm_d)
        scored.append((similarity, element, text))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        RetrievedChunk(source="vector", element=element, text=text, score=score)
        for score, element, text in scored[:top_k]
        if score > 0.0
    ]


def _openai_rank(query: str, chunks: list[tuple[str, str]], top_k: int) -> list[RetrievedChunk] | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not chunks:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=api_key)
    model = "text-embedding-3-small"
    texts = [query] + [text for _, text in chunks]
    response = client.embeddings.create(model=model, input=texts)
    vectors = [item.embedding for item in response.data]
    query_vec, doc_vecs = vectors[0], vectors[1:]

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (norm_a * norm_b)

    scored = [
        (cosine(query_vec, doc_vecs[i]), chunks[i][0], chunks[i][1]) for i in range(len(chunks))
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        RetrievedChunk(source="vector", element=element, text=text, score=score)
        for score, element, text in scored[:top_k]
    ]


class VectorRetriever:
    def __init__(self, top_k: int = 5, use_openai: bool | None = None) -> None:
        self.top_k = top_k
        self.use_openai = (
            bool(os.environ.get("OPENAI_API_KEY")) if use_openai is None else use_openai
        )

    def retrieve(self, query_text: str, module: Module) -> list[RetrievedChunk]:
        chunks = _chunks(module)
        if self.use_openai:
            result = _openai_rank(query_text, chunks, self.top_k)
            if result is not None:
                return result
        return _tfidf_rank(query_text, chunks, self.top_k)
