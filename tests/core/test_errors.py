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
