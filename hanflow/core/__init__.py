"""Core data contracts — the foundation of Hanflow.

All other modules depend only on ``hanflow.core`` plus their own boundary.
This package re-exports the public contract surface for convenience.
"""

from hanflow.core.errors import (
    BudgetExceededError,
    CheckpointCorruptError,
    CompileError,
    DSLValidationError,
    HanflowError,
    HITLTimeoutError,
    MaxDelegateDepthExceeded,
    MaxIterationsExceeded,
    MaxSubworkflowDepthExceeded,
    MCPConnectionError,
    ModelTimeoutError,
    NodeExecutionError,
    PrivacyViolationError,
    RateLimitError,
    ToolTimeoutError,
)

__all__ = [
    "BudgetExceededError",
    "CheckpointCorruptError",
    "CompileError",
    "DSLValidationError",
    "HanflowError",
    "HITLTimeoutError",
    "MaxDelegateDepthExceeded",
    "MaxIterationsExceeded",
    "MaxSubworkflowDepthExceeded",
    "MCPConnectionError",
    "ModelTimeoutError",
    "NodeExecutionError",
    "PrivacyViolationError",
    "RateLimitError",
    "ToolTimeoutError",
]
