"""GovernanceLayer — budget guard, rate limiting, cache, fallback (§4.5).

Cache: Phase 3 returns None / no-op (semantic cache is an extension point).
Rate limit: token-bucket per provider (rpm). Budget: raises BudgetExceededError
when an estimated cost would exceed the remaining run budget.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from hanflow.core.errors import BudgetExceededError, RateLimitError
from hanflow.models.strategies.base import ModelCandidate, RoutingRequest


class BudgetConfig(BaseModel):
    max_cost_per_run_usd: float = 1.0
    warn_at: float = 0.8


class RateLimitConfig(BaseModel):
    per_provider: dict[str, dict[str, int]] = {}  # {provider: {rpm, tpm}}


class CacheConfig(BaseModel):
    enabled: bool = False
    ttl_seconds: int = 3600


class GovernanceConfig(BaseModel):
    budget: BudgetConfig = BudgetConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    cache: CacheConfig = CacheConfig()
    fallback_chain: list[tuple[str, str]] = []


class GovernanceLayer:
    def __init__(self, config: GovernanceConfig) -> None:
        self.config = config
        # token bucket state: timestamps in the current 60s window, per provider
        self._calls: dict[str, list[float]] = {}

    async def check_budget(
        self,
        candidate: ModelCandidate,
        run_budget_remaining: float,
        estimated_cost: float = 0.0,
    ) -> None:
        if estimated_cost > run_budget_remaining + 1e-9:
            raise BudgetExceededError(
                f"estimated cost {estimated_cost} exceeds remaining budget {run_budget_remaining}",
                details={"provider": candidate.provider, "model": candidate.model},
            )

    async def acquire_rate_limit(self, provider: str) -> None:
        cfg = self.config.rate_limit.per_provider.get(provider)
        if cfg is None:
            return
        rpm = cfg.get("rpm", 0)
        if rpm <= 0:
            return
        now = time.monotonic()
        window = self._calls.setdefault(provider, [])
        window[:] = [t for t in window if now - t < 60.0]
        if len(window) >= rpm:
            raise RateLimitError(
                f"rate limit exceeded for {provider}: {rpm} rpm",
                details={"provider": provider, "rpm": rpm},
            )
        window.append(now)

    async def get_cached(self, request: RoutingRequest) -> Any:
        return None

    async def set_cached(self, request: RoutingRequest, response: Any) -> None:
        return None
