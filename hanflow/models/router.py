"""ModelRouter — collect strategy candidates, arbitrate by priority, govern, call.

Priority (detailed design §4.6):
    privacy(hard) > fallback(only on failure) > role > task > cost > static

Privacy is a one-vote veto (score=Inf). Fallback is a resilience mechanism,
not a routing strategy — it activates only after the primary provider fails.

Note on Phase 0 ↔ Phase 3 type consistency: the PUBLIC
RuntimeContext.complete(prefer: str | None) takes a *named model* string
(e.g. "strong") matching the ``models:`` config block (§4.7). The ModelRouter
is an internal API whose candidates deal in (provider, model) tuples. Phase 8
RuntimeContextImpl bridges the two: it resolves a named-model ``prefer`` string
to its (provider, model) tuple via the loaded config before calling
ModelRouter.complete(prefer=tuple, ...). Phase 3 therefore keeps the tuple
form internally.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from hanflow.core.errors import HanflowError, ModelTimeoutError
from hanflow.core.result import SensitivityLevel
from hanflow.models.providers.base import ModelResponse, StreamChunk
from hanflow.models.strategies.base import ModelCandidate, RoutingRequest
from hanflow.observability.trace import TraceExporter

DEFAULT_PRIORITY = ["privacy", "role", "task", "cost", "static"]


class ModelRouter:
    def __init__(
        self,
        providers: dict[str, Any],
        strategies: list[Any],
        governance: Any | None,
        trace: TraceExporter,
        default_model: tuple[str, str] | None = None,
    ) -> None:
        self.providers = providers
        self.strategies = strategies
        self.governance = governance
        self.trace = trace
        self.default_model = default_model

    async def complete(
        self,
        messages: list[Any],
        *,
        role: str | None = None,
        task_type: str | None = None,
        sensitivity: SensitivityLevel = "public",
        prefer: tuple[str, str] | None = None,
        run_budget_remaining: float = 1.0,
        **kwargs: Any,
    ) -> ModelResponse:
        request = RoutingRequest(
            messages=messages,
            role=role,
            task_type=task_type,
            sensitivity=sensitivity,
            prefer=prefer,
            run_budget_remaining=run_budget_remaining,
        )

        async with self.trace.span("llm.complete", kind="llm", role=role, task_type=task_type):
            candidates = self._collect_candidates(request)
            chosen = self._arbitrate(candidates, request)
            return await self._invoke_with_fallback(chosen, request, kwargs)

    async def stream(
        self,
        messages: list[Any],
        *,
        role: str | None = None,
        task_type: str | None = None,
        sensitivity: SensitivityLevel = "public",
        prefer: tuple[str, str] | None = None,
        run_budget_remaining: float = 1.0,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming variant of :meth:`complete` (§design Router.stream).

        Fallback semantics differ from the non-streaming path: a provider may
        only be swapped *before* the first chunk is yielded to the caller. The
        first chunk is therefore prefetched from each candidate in turn; once it
        succeeds the router commits to that provider and any subsequent
        mid-flight ``HanflowError`` propagates directly (the caller has already
        received partial output and a silent retry would be incorrect).
        """
        request = RoutingRequest(
            messages=messages,
            role=role,
            task_type=task_type,
            sensitivity=sensitivity,
            prefer=prefer,
            run_budget_remaining=run_budget_remaining,
        )
        async with self.trace.span("llm.stream", kind="llm", role=role, task_type=task_type):
            candidates = self._collect_candidates(request)
            chosen = self._arbitrate(candidates, request)
            async for chunk in self._stream_with_prefetch_fallback(chosen, request, kwargs):
                yield chunk

    async def _stream_with_prefetch_fallback(
        self,
        chosen: ModelCandidate,
        request: RoutingRequest,
        kwargs: dict[str, Any],
    ) -> AsyncIterator[StreamChunk]:
        """Prefetch the first chunk to decide whether to fall back.

        Order tried: ``chosen`` first, then each candidate of the fallback chain
        that is not the same (provider, model) pair. On a ``HanflowError`` before
        the first yield the next candidate is tried; once a first chunk has been
        yielded the stream is committed and later errors propagate unchanged.
        """
        # Dedup by (provider, model): chosen carries reason="default" while the
        # chain carries reason="fallback", so ModelCandidate equality would not
        # detect the same underlying provider/model pair.
        tried: set[tuple[str, str]] = {(chosen.provider, chosen.model)}
        chain: list[ModelCandidate] = [chosen]
        for cand in self._fallback_chain():
            key = (cand.provider, cand.model)
            if key in tried:
                continue
            tried.add(key)
            chain.append(cand)

        last_err: HanflowError | None = None
        for cand in chain:
            provider = self.providers.get(cand.provider)
            if provider is None:
                continue
            try:
                it = provider.stream(cand.model, request.messages, **kwargs)
                first = await it.__anext__()
            except HanflowError as e:
                # Failure before the first token: move to the next candidate.
                last_err = e
                continue
            except StopAsyncIteration:
                # Provider yielded nothing; treat as no output and try next.
                continue
            # First chunk obtained: commit to this provider, no further fallback.
            yield first
            async for chunk in it:
                yield chunk
            return

        if last_err is not None:
            raise last_err
        raise ModelTimeoutError("all providers failed before first stream token")

    # ---- candidate collection + arbitration ------------------------------ #
    def _collect_candidates(self, request: RoutingRequest) -> list[ModelCandidate]:
        out: list[ModelCandidate] = []
        for strat in self.strategies:
            out.extend(strat.candidates(request, self.providers))
        return out

    def _arbitrate(
        self, candidates: list[ModelCandidate], request: RoutingRequest
    ) -> ModelCandidate:
        if not candidates:
            if self.default_model is None:
                raise HanflowError("no model candidates and no default_model configured")
            provider, model = self.default_model
            return ModelCandidate(provider=provider, model=model, score=0.0, reason="default")

        # privacy veto: any candidate with reason containing 'privacy' wins outright
        privacy_hits = [c for c in candidates if "privacy" in c.reason.lower()]
        if privacy_hits:
            return max(privacy_hits, key=lambda c: c.score)

        def rank_key(c: ModelCandidate) -> tuple[int, float]:
            reason = c.reason.lower()
            for i, name in enumerate(DEFAULT_PRIORITY):
                if name in reason:
                    return (i, -c.score)
            return (len(DEFAULT_PRIORITY), -c.score)

        return min(candidates, key=rank_key)

    async def _invoke_with_fallback(
        self,
        chosen: ModelCandidate,
        request: RoutingRequest,
        kwargs: dict[str, Any],
    ) -> ModelResponse:
        if self.governance is not None:
            await self.governance.check_budget(
                chosen, request.run_budget_remaining, estimated_cost=0.0
            )
            await self.governance.acquire_rate_limit(chosen.provider)
            cached = await self.governance.get_cached(request)
            if cached is not None:
                return cast(ModelResponse, cached)
        try:
            provider = self.providers[chosen.provider]
            return cast(
                ModelResponse, await provider.complete(chosen.model, request.messages, **kwargs)
            )
        except HanflowError:
            chain = self._fallback_chain()
            for cand in chain:
                if cand == chosen:
                    continue
                try:
                    return cast(
                        ModelResponse,
                        await self.providers[cand.provider].complete(
                            cand.model, request.messages, **kwargs
                        ),
                    )
                except HanflowError:
                    continue
            raise

    def _fallback_chain(self) -> list[ModelCandidate]:
        for strat in self.strategies:
            if getattr(strat, "name", "") == "fallback":
                return list(strat.chain)
        return []
