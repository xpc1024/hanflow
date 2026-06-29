"""Unified exception hierarchy for Hanflow.

All framework errors descend from :class:`HanflowError`. Atoms and primitives
never swallow exceptions; the orchestration wrapper catches them, records
``NodeState.error`` + a trace error span, and decides next steps via
``on_error`` policy. ``retryable=True`` errors are eligible for automatic retry.
"""

from __future__ import annotations

from typing import Any


class HanflowError(Exception):
    """Base class for every Hanflow error.

    Attributes:
        code: Stable string error code (machine-readable).
        message: Human-readable description.
        retryable: Whether the caller may automatically retry on this error.
        run_id / node_id / span_id: Optional correlation coordinates.
        details: Arbitrary structured context.
    """

    code: str = "HANFLOW_ERROR"
    retryable: bool = False

    def __init__(
        self,
        message: str = "",
        *,
        run_id: str | None = None,
        node_id: str | None = None,
        span_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.run_id = run_id
        self.node_id = node_id
        self.span_id = span_id
        self.details = details or {}
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")

    def __str__(self) -> str:
        prefix = f"[{self.code}]"
        return f"{prefix} {self.message}" if self.message else prefix


class DSLValidationError(HanflowError):
    code = "DSL_INVALID"


class CompileError(HanflowError):
    code = "COMPILE_FAILED"


class NodeExecutionError(HanflowError):
    code = "NODE_FAILED"


class MaxIterationsExceeded(HanflowError):
    code = "MAX_ITER"


class HITLTimeoutError(HanflowError):
    code = "HITL_TIMEOUT"


class ModelTimeoutError(HanflowError):
    code = "MODEL_TIMEOUT"
    retryable = True


class RateLimitError(HanflowError):
    code = "MODEL_RATE_LIMIT"
    retryable = True


class BudgetExceededError(HanflowError):
    code = "BUDGET_EXCEEDED"


class PrivacyViolationError(HanflowError):
    code = "PRIVACY_VIOLATION"


class ToolTimeoutError(HanflowError):
    code = "TOOL_TIMEOUT"
    retryable = True


class MCPConnectionError(HanflowError):
    code = "MCP_CONN_FAILED"
    retryable = True


class CheckpointCorruptError(HanflowError):
    code = "CHECKPOINT_CORRUPT"


class MaxDelegateDepthExceeded(HanflowError):
    code = "DELEGATE_DEPTH"


class MaxSubworkflowDepthExceeded(HanflowError):
    code = "SUBWORKFLOW_DEPTH"
