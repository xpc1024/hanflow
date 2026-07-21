"""Core data contracts — the foundation of Hanflow.

All other modules depend only on ``hanflow.core`` plus their own boundary.
This package re-exports the public contract surface for convenience.
"""

from hanflow.core.context import FakeContext, RuntimeContext
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
    SandboxDependencyMissingError,
    SandboxDestroyFailedError,
    SandboxError,
    SandboxProvisionFailedError,
    SandboxTimeoutError,
    ToolTimeoutError,
    ToolWhitelistError,
)
from hanflow.core.result import (
    Artifact,
    AtomResult,
    Chunk,
    HITLPayload,
    HITLRecord,
    MemoryOp,
    NextAction,
    ResearchNote,
    SensitivityLevel,
    Source,
    TraceEvent,
)

__all__ = [
    # context
    "FakeContext",
    "RuntimeContext",
    # errors
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
    "SandboxDependencyMissingError",
    "SandboxDestroyFailedError",
    "SandboxError",
    "SandboxProvisionFailedError",
    "SandboxTimeoutError",
    "ToolTimeoutError",
    "ToolWhitelistError",
    # result
    "Artifact",
    "AtomResult",
    "Chunk",
    "HITLPayload",
    "HITLRecord",
    "MemoryOp",
    "NextAction",
    "ResearchNote",
    "SensitivityLevel",
    "Source",
    "TraceEvent",
]
