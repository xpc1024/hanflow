import pytest

from hanflow.core.errors import BudgetExceededError, RateLimitError
from hanflow.models.governance import (
    BudgetConfig,
    GovernanceConfig,
    GovernanceLayer,
    RateLimitConfig,
)
from hanflow.models.strategies.base import ModelCandidate, RoutingRequest


@pytest.mark.asyncio
async def test_budget_exceeded_raises():
    g = GovernanceLayer(
        GovernanceConfig(budget=BudgetConfig(max_cost_per_run_usd=1.0, warn_at=0.8))
    )
    cand = ModelCandidate(provider="cloud", model="strong", score=1.0, reason="static")
    with pytest.raises(BudgetExceededError):
        await g.check_budget(cand, run_budget_remaining=0.4, estimated_cost=0.5)


@pytest.mark.asyncio
async def test_budget_warn_but_ok():
    g = GovernanceLayer(
        GovernanceConfig(budget=BudgetConfig(max_cost_per_run_usd=1.0, warn_at=0.8))
    )
    cand = ModelCandidate(provider="cloud", model="strong", score=1.0, reason="static")
    await g.check_budget(cand, run_budget_remaining=0.4, estimated_cost=0.05)


@pytest.mark.asyncio
async def test_rate_limit_token_bucket():
    g = GovernanceLayer(
        GovernanceConfig(
            rate_limit=RateLimitConfig(per_provider={"cloud": {"rpm": 2, "tpm": 10000}})
        )
    )
    await g.acquire_rate_limit("cloud")
    await g.acquire_rate_limit("cloud")
    with pytest.raises(RateLimitError):
        await g.acquire_rate_limit("cloud")


@pytest.mark.asyncio
async def test_cache_returns_none_by_default():
    g = GovernanceLayer(GovernanceConfig())
    req = RoutingRequest(messages=[{"role": "user", "content": "hi"}])
    assert await g.get_cached(req) is None
    await g.set_cached(req, object())  # no-op, no crash
