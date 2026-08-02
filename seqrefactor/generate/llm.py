"""LLM adapter (Software Specification §5.7, NFR-2).

Generates a candidate refactoring via the OpenAI API, grounded in the
retrieved context (seqrefactor.retrieve.retriever). NFR-2 requires that "LLM
outputs [be] recorded and replayed on reproduce, never re-queried": every
call is cached to disk keyed by a content hash of (target, context, seed,
model), so a `reproduce` run never touches the network and byte-for-byte
replays what a `run` produced (see jvm-sidecar-style JSON-on-disk pattern
used throughout this project for cross-process reproducibility).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from seqrefactor import _treesitter as ts
from seqrefactor.model import Candidate, GenContext, Module, SmellInstance

NAME = "llm"
DEFAULT_CACHE_DIR = Path(
    os.environ.get("SEQREFACTOR_LLM_CACHE_DIR", Path.cwd() / "runs" / "llm_cache")
)
DEFAULT_MODEL = os.environ.get("SEQREFACTOR_LLM_MODEL", "gpt-4.1-mini")

_PATCH_FENCE_RE = re.compile(r"```(?:java)?\s*\n(.*?)```", re.DOTALL)

_SYSTEM_PROMPT = (
    "You are a careful refactoring assistant. You will be given one Java method "
    "flagged with a code smell, plus retrieved context from the same module. "
    "Return ONLY the complete rewritten source file (the same class, fully "
    "qualified, compilable) inside a single ```java fenced code block, with no "
    "commentary before or after. Preserve external behaviour exactly: do not "
    "change what the code does, only its internal structure."
)


class LLMUnavailable(RuntimeError):
    pass


def _cache_key(target: SmellInstance, ctx: GenContext, seed: int, model: str) -> str:
    payload = json.dumps(
        {
            "smell": target.model_dump(),
            "chunks": [c.model_dump() for c in ctx.chunks],
            "seed": seed,
            "model": model,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _build_prompt(target: SmellInstance, ctx: GenContext, module: Module) -> str:
    element = target.loc[0] if target.loc else target.category
    matching_file = ts.locate_file(element, module.source_files)
    source_snippet = (
        matching_file.read_text(encoding="utf-8", errors="replace") if matching_file else ""
    )

    context_lines = "\n\n".join(f"# {c.source}: {c.element}\n{c.text}" for c in ctx.chunks[:5])
    return (
        f"Smell: {target.category} at {element} (severity {target.severity:.2f}).\n\n"
        f"Retrieved context:\n{context_lines}\n\n"
        f"Full source file to refactor:\n```java\n{source_snippet}\n```"
    )


def refactor(
    target: SmellInstance,
    ctx: GenContext,
    module: Module,
    seed: int = 0,
    model: str = DEFAULT_MODEL,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Candidate:
    key = _cache_key(target, ctx, seed, model)
    cache_file = _cache_path(cache_dir, key)

    if cache_file.is_file():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        raw_output = cached["raw_output"]
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LLMUnavailable(
                "OPENAI_API_KEY is not set and no cached response exists at "
                f"{cache_file}. Set the key to generate, or run with a pre-populated "
                "cache to reproduce (NFR-2: raw outputs are recorded, never re-queried)."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMUnavailable("the `openai` package is not installed") from exc

        client = OpenAI(api_key=api_key)
        prompt = _build_prompt(target, ctx, module)
        response = client.chat.completions.create(
            model=model,
            seed=seed,
            temperature=0.0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw_output = response.choices[0].message.content or ""

        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(
                {
                    "target": target.id,
                    "model": model,
                    "seed": seed,
                    "raw_output": raw_output,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    match = _PATCH_FENCE_RE.search(raw_output)
    patch = match.group(1) if match else ""

    return Candidate(
        smell=target.id,
        generator=NAME,
        patch=patch,
        raw_output=raw_output,
        seed=seed,
    )
