"""Combined Retriever (Software Specification §5.6): fuses vector and structural
retrieval into a single ``GenContext`` for the generator."""

from __future__ import annotations

from seqrefactor.model import GenContext, Module, SmellInstance
from seqrefactor.retrieve.cpg import StructuralRetriever
from seqrefactor.retrieve.vector import VectorRetriever


class Retriever:
    def __init__(
        self,
        vector: VectorRetriever | None = None,
        structural: StructuralRetriever | None = None,
    ) -> None:
        self.vector = vector or VectorRetriever()
        self.structural = structural or StructuralRetriever()

    def context(self, target: SmellInstance, module: Module) -> GenContext:
        element = target.loc[0] if target.loc else target.category
        query = f"{target.category} in {element}"

        chunks = list(self.vector.retrieve(query, module))
        chunks.extend(self.structural.retrieve(element, module))

        return GenContext(target=target.id, chunks=chunks)
