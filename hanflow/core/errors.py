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


class CLIError(HanflowError):
    """CLI operation error (connection failed / not found / conflict)."""

    code = "CLI_ERROR"


# --- Sandbox error hierarchy (cycle 2026-W30-1.1.1: DOCKER sandbox provisioner) ---
# 子类通过覆盖类属性 code/retryable 区分具体场景; __init__ 继承基类, 不传 code= kwarg。
# §2.1 统一错误层级: atoms 永不吞异常, 由 orchestration 包装层捕获后记录 trace + on_error。


class SandboxError(HanflowError):
    """Sandbox provisioning/destroy/exec 失败的基类 (§13.6, §5.3)."""

    code = "SANDBOX_ERROR"


class SandboxProvisionFailedError(SandboxError):
    """容器创建/启动失败, 或不支持的 sandbox mode。非 retryable (通常配置错)。"""

    code = "SANDBOX_PROVISION_FAILED"


class SandboxDestroyFailedError(SandboxError):
    """容器销毁失败。retryable (container 可能 leak, 重试可能成功)。"""

    code = "SANDBOX_DESTROY_FAILED"
    retryable = True


class SandboxTimeoutError(SandboxError):
    """exec 或 provision 超时。retryable (换环境/换 daemon 可能成功)。"""

    code = "SANDBOX_TIMEOUT"
    retryable = True


class SandboxDependencyMissingError(SandboxError):
    """aiodocker 等依赖未安装。非 retryable (需 pip install)。"""

    code = "SANDBOX_DEP_MISSING"


class ToolWhitelistError(HanflowError):
    """工具调用不在 sub-agent 白名单内。

    顺手清理 (cycle 2026-W30-1.1.1): 原 enforce_tool_whitelist 滥用基类 HanflowError,
    现改用专用子类, 与其它领域错误一致。
    """

    code = "TOOL_WHITELIST"
