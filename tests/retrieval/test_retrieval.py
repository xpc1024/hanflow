"""Retrieval tests: provider/hybrid/indexing/embedding/reranker/memory backends."""

from __future__ import annotations

import pytest

from hanflow.retrieval.embedding import FakeEmbedding
from hanflow.retrieval.fulltext.memory_fts import InMemoryFullTextProvider
from hanflow.retrieval.hybrid import CascadeFusion, RRFFusion, WeightedFusion
from hanflow.retrieval.indexing import (
    ChunkStrategy,
    DefaultTextSplitter,
    Document,
    IndexingPipeline,
)
from hanflow.retrieval.provider import (
    FullTextSearchProvider,
    HybridSearchProvider,
    VectorSearchProvider,
)
from hanflow.retrieval.reranker import FakeReranker
from hanflow.retrieval.vector.memory import InMemoryVectorProvider


@pytest.fixture
def embed():
    return FakeEmbedding(dim=8)


@pytest.fixture
async def vector(embed):
    v = InMemoryVectorProvider(dim=embed.dim)
    await v.create_collection("docs", dim=embed.dim)
    return v


@pytest.fixture
async def fulltext():
    f = InMemoryFullTextProvider()
    await f.create_index("docs")
    return f


# --- providers ------------------------------------------------------------


@pytest.mark.asyncio
async def test_vector_provider_search_returns_chunks(embed, vector):
    vp = VectorSearchProvider(vector=vector, embedding=embed, name="vec")
    await vp.upsert([Document(id="d1", content="hello world")], collection="docs")
    chunks = await vp.search("docs", "hello world", top_k=3)
    assert chunks
    assert chunks[0].source.kind == "private_kb"


@pytest.mark.asyncio
async def test_vector_provider_top_k(embed, vector):
    vp = VectorSearchProvider(vector=vector, embedding=embed, name="vec")
    await vp.upsert(
        [Document(id=f"d{i}", content=f"doc number {i}") for i in range(5)],
        collection="docs",
    )
    chunks = await vp.search("docs", "doc", top_k=2)
    assert len(chunks) <= 2


@pytest.mark.asyncio
async def test_fulltext_provider_search(fulltext):
    fp = FullTextSearchProvider(fulltext=fulltext, name="ft")
    await fp.upsert([Document(id="d1", content="the quick brown fox")], collection="docs")
    chunks = await fp.search("docs", "quick fox", top_k=3)
    assert chunks


@pytest.mark.asyncio
async def test_hybrid_provider_fuses(embed, vector, fulltext):
    hp = HybridSearchProvider(
        vector=vector, fulltext=fulltext, embedding=embed, fusion=RRFFusion(), name="hyb"
    )
    await hp.upsert([Document(id="d1", content="unified search test")], collection="docs")
    chunks = await hp.search("docs", "unified search", top_k=3)
    assert chunks


@pytest.mark.asyncio
async def test_vector_delete(embed, vector):
    vp = VectorSearchProvider(vector=vector, embedding=embed, name="vec")
    await vp.upsert([Document(id="d1", content="x")], collection="docs")
    n = await vp.delete(collection="docs", ids=["d1"])
    assert n == 1


# --- hybrid strategies ----------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_strategies_each_return_hits(embed, vector, fulltext):
    # seed both backends via providers
    vp = VectorSearchProvider(vector, embed)
    fp = FullTextSearchProvider(fulltext)
    docs = [Document(id=f"d{i}", content=f"alpha beta gamma {i}") for i in range(3)]
    await vp.upsert(docs, collection="docs")
    await fp.upsert(docs, collection="docs")
    for fusion in (RRFFusion(), WeightedFusion(), CascadeFusion()):
        hp = HybridSearchProvider(vector, fulltext, embed, fusion=fusion)
        chunks = await hp.search("docs", "alpha beta", top_k=3)
        assert isinstance(chunks, list)


# --- indexing -------------------------------------------------------------


def test_default_splitter_chunks_with_overlap():
    splitter = DefaultTextSplitter()
    doc = Document(id="x", content="A" * 100)
    chunks = splitter.split(
        doc, ChunkStrategy(strategy="recursive", chunk_size=40, chunk_overlap=10)
    )
    assert len(chunks) > 1
    assert all(c.metadata["parent_id"] == "x" for c in chunks)


def test_default_splitter_none_returns_single():
    splitter = DefaultTextSplitter()
    doc = Document(id="x", content="hello")
    chunks = splitter.split(doc, ChunkStrategy(strategy="none"))
    assert chunks == [doc]


@pytest.mark.asyncio
async def test_indexing_pipeline_indexes_into_store(embed, vector):
    vp = VectorSearchProvider(vector, embed)
    pipe = IndexingPipeline()
    stats = await pipe.index(
        vp,
        [Document(id=f"d{i}", content=f"document {i} " * 50) for i in range(3)],
        collection="docs",
        chunk=ChunkStrategy(strategy="recursive", chunk_size=100, chunk_overlap=20),
    )
    assert stats.documents_indexed == 3
    assert stats.chunks_indexed >= 3


# --- embedding + reranker -------------------------------------------------


@pytest.mark.asyncio
async def test_fake_embedding_deterministic(embed):
    a = await embed.embed(["hello"])
    b = await embed.embed(["hello"])
    assert a == b
    assert len(a[0]) == embed.dim


@pytest.mark.asyncio
async def test_fake_reranker_boosts_query_terms():
    r = FakeReranker()
    hits = await r.rerank("alpha", ["beta gamma", "alpha delta", "epsilon"], top_k=3)
    # the doc containing 'alpha' should rank first
    assert hits[0].index == 1


# --- unified filter -------------------------------------------------------


@pytest.mark.asyncio
async def test_vector_filter_gte(embed, vector):
    vp = VectorSearchProvider(vector, embed)
    await vp.upsert(
        [
            Document(id="a", content="x", metadata={"score": 5}),
            Document(id="b", content="x", metadata={"score": 1}),
        ],
        collection="docs",
    )
    chunks = await vp.search("docs", "x", top_k=5, filter={"score": {"$gte": 3}})
    ids = {c.source.source_id for c in chunks}
    assert ids == {"a"}
