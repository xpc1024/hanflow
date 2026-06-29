import pytest

from hanflow.core.expr import ExprError, evaluate, interpolate

# --- interpolation ---------------------------------------------------------


def test_interpolate_basic():
    out = interpolate("Hello {{name}}!", {"name": "Han"})
    assert out == "Hello Han!"


def test_interpolate_nested_access():
    out = interpolate("{{a.b.c}}", {"a": {"b": {"c": 42}}})
    assert out == "42"


def test_interpolate_index_access():
    out = interpolate("{{items.0}}", {"items": ["x", "y"]})
    assert out == "x"


def test_interpolate_missing_raises():
    with pytest.raises(ExprError):
        interpolate("{{ghost}}", {})


def test_interpolate_multiple_in_one_string():
    out = interpolate("{{a}}+{{b}}={{c}}", {"a": 1, "b": 2, "c": 3})
    assert out == "1+2=3"


def test_interpolate_no_placeholders_unchanged():
    assert interpolate("plain text", {}) == "plain text"


# --- evaluation (condition language) ---------------------------------------


def test_eval_equals_string():
    assert evaluate("action == 'approve'", {"action": "approve"}) is True
    assert evaluate("action == 'approve'", {"action": "reject"}) is False


def test_eval_not_equal():
    assert evaluate("status != 'done'", {"status": "running"}) is True


def test_eval_in_list():
    assert (
        evaluate("sensitivity in [confidential, restricted]", {"sensitivity": "restricted"}) is True
    )
    assert evaluate("sensitivity in [confidential, restricted]", {"sensitivity": "public"}) is False


def test_eval_and_or():
    assert evaluate("a == 1 and b == 2", {"a": 1, "b": 2}) is True
    assert evaluate("a == 1 or b == 9", {"a": 1, "b": 2}) is True
    assert evaluate("a == 1 and b == 9", {"a": 1, "b": 2}) is False


def test_eval_field_access_via_dotted():
    # Dotted name resolves to nested dict path (used by node refs like review.action)
    assert evaluate("review.action == 'approve'", {"review": {"action": "approve"}}) is True


def test_eval_unknown_variable_raises():
    with pytest.raises(ExprError):
        evaluate("ghost == 1", {})


def test_eval_rejects_unsafe_constructs():
    # The engine must NOT allow arbitrary expressions — only the supported grammar.
    with pytest.raises(ExprError):
        evaluate("__import__('os')", {})


def test_condition_uses_dotted_path_against_live_context():
    # Conditions are evaluated against the live context with dotted-path
    # resolution (this is how the engine runs Branch nodes). A templated
    # condition like "{{review.action}} == 'approve'" is evaluated as the
    # bare dotted path "review.action == 'approve'" with the context present.
    assert evaluate("review.action == 'approve'", {"review": {"action": "approve"}}) is True
    assert evaluate("review.action == 'approve'", {"review": {"action": "reject"}}) is False
