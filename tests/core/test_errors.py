import pytest

from hanflow.core.errors import (
    BudgetExceededError,
    CheckpointCorruptError,
    CLIError,
    CompileError,
    DSLValidationError,
    HanflowError,
    HITLTimeoutError,
    MaxDelegateDepthExceeded,
    MaxIterationsExceeded,
    MaxSubworkflowDepthExceeded,
    MCPConnectionError,
    ModelTimeoutError,
    SandboxDependencyMissingError,
    SandboxDestroyFailedError,
    SandboxError,
    SandboxProvisionFailedError,
    SandboxTimeoutError,
    ToolWhitelistError,
    NodeExecutionError,
    PrivacyViolationError,
    RateLimitError,
    ToolTimeoutError,
)


def test_base_error_carries_code_and_message():
    err = DSLValidationError("bad node", run_id="r1", node_id="n1")
    assert isinstance(err, HanflowError)
    assert err.code == "DSL_INVALID"
    assert err.message == "bad node"
    assert err.run_id == "r1"
    assert err.node_id == "n1"
    assert err.retryable is False


def test_retryable_flags():
    assert ModelTimeoutError("t").retryable is True
    assert RateLimitError("t").retryable is True
    assert ToolTimeoutError("t").retryable is True
    assert MCPConnectionError("t").retryable is True
    assert NodeExecutionError("t").retryable is False
    assert BudgetExceededError("t").retryable is False
    assert PrivacyViolationError("t").retryable is False


def test_error_codes_are_unique():
    codes = [
        DSLValidationError("").code,
        CompileError("").code,
        NodeExecutionError("").code,
        MaxIterationsExceeded("").code,
        HITLTimeoutError("").code,
        ModelTimeoutError("").code,
        RateLimitError("").code,
        BudgetExceededError("").code,
        PrivacyViolationError("").code,
        ToolTimeoutError("").code,
        MCPConnectionError("").code,
        CheckpointCorruptError("").code,
        MaxDelegateDepthExceeded("").code,
        MaxSubworkflowDepthExceeded("").code,
    ]
    assert len(codes) == len(set(codes)), "duplicate error codes"


def test_error_carries_details():
    err = CompileError("failed", details={"node": "n1", "reason": "cycle"})
    assert err.details == {"node": "n1", "reason": "cycle"}


def test_error_str_contains_code_and_message():
    err = PrivacyViolationError("leak")
    s = str(err)
    assert "PRIVACY_VIOLATION" in s
    assert "leak" in s


def test_can_be_raised_and_caught_as_base():
    with pytest.raises(HanflowError) as exc_info:
        raise BudgetExceededError("over")
    assert exc_info.value.code == "BUDGET_EXCEEDED"


def test_cli_error_has_stable_code():
    err = CLIError("run not found: abc")
    assert isinstance(err, HanflowError)
    assert err.code == "CLI_ERROR"
    assert err.retryable is False
    assert "CLI_ERROR" in str(err)
    assert "run not found: abc" in str(err)


# --- Sandbox error hierarchy (cycle 2026-W30-1.1.1) ---


def test_sandbox_error_is_hanflow_error():
    assert issubclass(SandboxError, HanflowError)


def test_sandbox_error_code_is_class_attr():
    """code 是类属性, 不是 __init__ kwarg(关键: 审计 round 1 修订)。"""
    assert SandboxError.code == "SANDBOX_ERROR"
    assert SandboxProvisionFailedError.code == "SANDBOX_PROVISION_FAILED"
    assert SandboxDestroyFailedError.code == "SANDBOX_DESTROY_FAILED"
    assert SandboxTimeoutError.code == "SANDBOX_TIMEOUT"
    assert SandboxDependencyMissingError.code == "SANDBOX_DEP_MISSING"
    assert ToolWhitelistError.code == "TOOL_WHITELIST"


def test_sandbox_error_init_does_not_accept_code_kwarg():
    """验证 __init__ 签名不含 code(回归审计 round 1 严重 #1)。"""
    with pytest.raises(TypeError):
        SandboxError("msg", code="X")  # type: ignore[call-arg]


def test_sandbox_subclasses_inherit_init():
    """子类继承基类 __init__, 只覆盖类属性 code/retryable。"""
    err = SandboxProvisionFailedError("provision failed", run_id="r1", details={"k": "v"})
    assert err.code == "SANDBOX_PROVISION_FAILED"
    assert err.retryable is False  # 默认
    assert err.run_id == "r1"
    assert err.details == {"k": "v"}


def test_sandbox_retryable_semantics():
    """retryable 语义: timeout/destroy 可重试, provision/dep_missing 不可。"""
    assert SandboxProvisionFailedError.retryable is False
    assert SandboxDestroyFailedError.retryable is True
    assert SandboxTimeoutError.retryable is True
    assert SandboxDependencyMissingError.retryable is False


def test_sandbox_destroy_inherits_from_sandbox():
    """Sandbox 子类层级正确。"""
    assert issubclass(SandboxDestroyFailedError, SandboxError)
    assert issubclass(SandboxTimeoutError, SandboxError)
    assert issubclass(SandboxProvisionFailedError, SandboxError)
    assert issubclass(SandboxDependencyMissingError, SandboxError)


def test_sandbox_error_str_contains_code_and_message():
    err = SandboxTimeoutError("timed out", run_id="r1")
    assert "SANDBOX_TIMEOUT" in str(err)
    assert "timed out" in str(err)


def test_tool_whitelist_error_is_hanflow_error():
    assert issubclass(ToolWhitelistError, HanflowError)
    assert ToolWhitelistError.code == "TOOL_WHITELIST"
    assert ToolWhitelistError.retryable is False


def test_can_raise_sandbox_error_and_catch_as_base():
    """统一错误层级: 任何 SandboxError 子类可被 HanflowError except 捕获。"""
    with pytest.raises(HanflowError) as exc_info:
        raise SandboxDestroyFailedError("kill failed", run_id="r1")
    assert exc_info.value.code == "SANDBOX_DESTROY_FAILED"
    assert exc_info.value.retryable is True
