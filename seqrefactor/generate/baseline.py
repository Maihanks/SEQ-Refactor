"""Deterministic Extract-Method baseline generator (Software Specification §5.7, §8.3).

Its role in the ablation is to be a non-LLM generator level, so ordering
effects are visible independently of generation quality (paper §Variables:
"the generator is a controlled factor... an in-house deterministic Extract
Method baseline"). It is deliberately NOT a sophisticated refactoring engine:
it performs the smallest transformation that is (a) always behaviour
preserving by construction and (b) fully deterministic given the same
input -- it extracts the flagged method's entire body into a new private
`<name>Extracted` method and replaces the body with a single delegating
call. This does not, by itself, resolve a LongMethod/BigSwitch/MessageChains
smell (a real Extract Method needs to choose a meaningful sub-block, which
requires semantic reasoning about the "why" seqrefactor.generate.llm is for);
it exists so the pipeline and the ablation have a deterministic control, not
to be evaluated as a quality refactoring tool.
"""

from __future__ import annotations

import hashlib

from seqrefactor import _treesitter as ts
from seqrefactor.model import Candidate, GenContext, Module, SmellInstance

NAME = "baseline"


def _find_method(module: Module, qualified_method_name: str) -> tuple[ts.JavaClass, ts.JavaMethod, str] | None:
    for source_file in module.source_files:
        for cls in ts.parse_file(source_file):
            for method in cls.methods:
                if method.qualified_name == qualified_method_name:
                    return cls, method, source_file.read_text(encoding="utf-8")
    return None


def _parse_param_names(signature: str, method_name: str) -> list[str]:
    """Extract parameter names from a method signature by matching the parens after
    ``method_name(``. Naive top-level comma split -- correct for simple, non-generic
    parameter types (this project's fixtures), not a full Java parameter-list parser."""
    marker = f"{method_name}("
    idx = signature.find(marker)
    if idx == -1:
        return []
    start = idx + len(marker)
    depth = 1
    pos = start
    while pos < len(signature) and depth > 0:
        if signature[pos] == "(":
            depth += 1
        elif signature[pos] == ")":
            depth -= 1
        pos += 1
    params_str = signature[start : pos - 1]
    names = []
    for part in params_str.split(","):
        part = part.strip()
        if part:
            names.append(part.split()[-1].lstrip("[]"))
    return names


def _extract_wrapper_patch(source_text: str, method: ts.JavaMethod) -> str | None:
    lines = source_text.splitlines(keepends=True)
    start, end = method.start_line - 1, method.end_line  # 0-indexed, end exclusive
    original = "".join(lines[start:end])

    body_open = original.find("{")
    body_close = original.rfind("}")
    if body_open == -1 or body_close == -1:
        return None  # abstract/interface method with no body -- nothing to extract

    signature = original[:body_open]
    body = original[body_open + 1 : body_close]
    extracted_name = f"{method.name}Extracted"
    param_names = _parse_param_names(signature, method.name)
    args = ", ".join(param_names)

    is_void = "void" in signature.split("(")[0]
    call_expr = (
        f"        {extracted_name}({args});\n"
        if is_void
        else f"        return {extracted_name}({args});\n"
    )

    wrapper = f"{signature}{{\n{call_expr}    }}\n\n"
    # Keep the original modifiers/return type; only the method name changes, so the
    # extracted helper stays whatever visibility the original method had.
    extracted_signature = signature.replace(f" {method.name}(", f" {extracted_name}(", 1)
    extracted = f"{extracted_signature}{{{body}}}\n"

    new_text = "".join(lines[:start]) + wrapper + extracted + "".join(lines[end:])
    return new_text


def refactor(target: SmellInstance, ctx: GenContext, module: Module, seed: int = 0) -> Candidate:
    del ctx  # the deterministic baseline does not use retrieved context, unlike the LLM adapter
    qualified_method = target.loc[0] if target.loc else ""
    found = _find_method(module, qualified_method)

    if found is None:
        return Candidate(
            smell=target.id,
            generator=NAME,
            patch="",
            raw_output=f"no method-level element found for loc={target.loc!r}; baseline is a no-op for class-level smells",
            seed=seed,
        )

    cls, method, source_text = found
    new_text = _extract_wrapper_patch(source_text, method)
    if new_text is None:
        return Candidate(
            smell=target.id,
            generator=NAME,
            patch="",
            raw_output=f"method {method.qualified_name} has no body to extract (abstract/interface)",
            seed=seed,
        )

    digest = hashlib.sha256(new_text.encode("utf-8")).hexdigest()[:12]
    return Candidate(
        smell=target.id,
        generator=NAME,
        patch=new_text,
        raw_output=f"extract-wrapper applied to {method.qualified_name}; content_hash={digest}",
        seed=seed,
    )
