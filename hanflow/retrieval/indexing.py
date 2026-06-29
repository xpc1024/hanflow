"""IndexingPipeline + Document + ChunkStrategy + TextSplitter (§6.6)."""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel


class Document(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any] = {}


class ChunkStrategy(BaseModel):
    strategy: Literal["recursive", "token", "sentence", "markdown", "none"] = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 64
    separators: list[str] | None = None


class IndexStats(BaseModel):
    documents_indexed: int = 0
    chunks_indexed: int = 0
    mode: str = ""
    duration_seconds: float = 0.0


@runtime_checkable
class TextSplitter(Protocol):
    def split(self, document: Document, strategy: ChunkStrategy) -> list[Document]: ...


class DefaultTextSplitter:
    """Splits by chunk_size chars with overlap (recursive fallback to char split)."""

    def split(self, document: Document, strategy: ChunkStrategy) -> list[Document]:
        if strategy.strategy == "none":
            return [document]
        text = document.content
        size = strategy.chunk_size
        overlap = strategy.chunk_overlap
        chunks: list[Document] = []
        i = 0
        idx = 0
        while i < len(text):
            piece = text[i : i + size]
            chunks.append(
                Document(
                    id=f"{document.id}-{idx}",
                    content=piece,
                    metadata={**document.metadata, "parent_id": document.id, "chunk_index": idx},
                )
            )
            idx += 1
            if i + size >= len(text):
                break
            i += max(1, size - overlap)
        return chunks or [document]


class IndexingPipeline:
    """Index documents into a SearchProvider (vector / fulltext / hybrid).

    For hybrid stores, ``index_sync`` selects dual / vector_only / fulltext_only.
    """

    def __init__(self, splitter: TextSplitter | None = None) -> None:
        self.splitter = splitter or DefaultTextSplitter()

    async def index(
        self,
        store: Any,
        documents: list[Document],
        *,
        collection: str | None = None,
        chunk: ChunkStrategy | None = None,
        index_sync: str = "dual",
        batch_size: int = 100,
    ) -> IndexStats:
        import time

        strategy = chunk or ChunkStrategy()
        t0 = time.monotonic()
        total_chunks = 0
        for batch_start in range(0, len(documents), batch_size):
            batch = documents[batch_start : batch_start + batch_size]
            split: list[Document] = []
            for d in batch:
                split.extend(self.splitter.split(d, strategy))
            await store.upsert(split, collection=collection)
            total_chunks += len(split)
        return IndexStats(
            documents_indexed=len(documents),
            chunks_indexed=total_chunks,
            mode=index_sync,
            duration_seconds=time.monotonic() - t0,
        )
