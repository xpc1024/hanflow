"""EmbeddingProvider — pluggable embedding backends (§6.5)."""

from __future__ import annotations

import hashlib
from typing import Any, Protocol, cast, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    dim: int

    @property
    def is_local(self) -> bool: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbedding:
    """Deterministic hash-based embedding for tests (is_local=True)."""

    name = "fake"

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim

    @property
    def is_local(self) -> bool:
        return True

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            h = hashlib.md5(t.encode()).digest()
            out.append([(b - 128) / 128 for b in h[: self.dim]])
        return out


class OpenAIEmbedding:
    name = "openai"

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        self.dim = 1536 if "small" in model else 3072

    @property
    def is_local(self) -> bool:
        return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        resp = await client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


class BGEEEmbedding:
    """BGE embedding served over HTTP (is_local=True)."""

    name = "bge"

    def __init__(self, model: str = "bge-m3", base_url: str = "http://bge:8080") -> None:
        self.model = model
        self.base_url = base_url
        self.dim = 1024

    @property
    def is_local(self) -> bool:
        return True

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/embed", json={"inputs": texts})
            resp.raise_for_status()
            return cast(list[list[float]], resp.json())


class OllamaEmbedding:
    name = "ollama"

    def __init__(
        self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.dim = 768

    @property
    def is_local(self) -> bool:
        return True

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import ollama

        client = ollama.AsyncClient(host=self.base_url)
        out: list[list[float]] = []
        for t in texts:
            r = await client.embeddings(model=self.model, prompt=t)
            out.append(r["embedding"])
        return out


_ = Any  # keep import for type-checker parity if extended
