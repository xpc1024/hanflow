import pytest

from hanflow.core.errors import PrivacyViolationError
from hanflow.models.privacy import PIIConfig, PrivacyConfig, PrivacyStrategy
from hanflow.models.strategies.base import RoutingRequest


def _providers():
    from tests.models.conftest import FakeProvider

    return {
        "cloud": FakeProvider("cloud", is_local=False),
        "local": FakeProvider("local", is_local=True),
    }


def test_confidential_routes_to_local_only():
    strat = PrivacyStrategy(
        PrivacyConfig(
            local_providers=["local"], enforce="hard", pii_detection=PIIConfig(regex=True)
        )
    )
    req = RoutingRequest(messages=[], sensitivity="confidential")
    cands = strat.candidates(req, _providers())
    assert len(cands) == 1
    assert cands[0].provider == "local"
    assert cands[0].score == float("inf")
    assert "privacy" in cands[0].reason


def test_internal_no_pii_does_not_engage():
    strat = PrivacyStrategy(
        PrivacyConfig(local_providers=["local"], pii_detection=PIIConfig(regex=True))
    )
    req = RoutingRequest(messages=[], sensitivity="internal")
    assert strat.candidates(req, _providers()) == []


def test_pii_detected_routes_local_and_marks_redact():
    strat = PrivacyStrategy(
        PrivacyConfig(local_providers=["local"], pii_detection=PIIConfig(regex=True))
    )
    req = RoutingRequest(
        messages=[{"role": "user", "content": "my email is alice@example.com"}],
        sensitivity="public",
    )
    cands = strat.candidates(req, _providers())
    assert len(cands) == 1
    assert cands[0].provider == "local"
    assert "redact" in cands[0].reason.lower()


def test_hard_violation_when_no_local_provider():
    from tests.models.conftest import FakeProvider

    strat = PrivacyStrategy(
        PrivacyConfig(
            local_providers=["local"], enforce="hard", pii_detection=PIIConfig(regex=True)
        )
    )
    provs = {"cloud": FakeProvider("cloud", is_local=False)}  # no local
    req = RoutingRequest(messages=[], sensitivity="restricted")
    with pytest.raises(PrivacyViolationError):
        strat.candidates(req, provs)


@pytest.mark.asyncio
async def test_redact_replaces_pii_and_returns_map():
    strat = PrivacyStrategy(
        PrivacyConfig(local_providers=["local"], pii_detection=PIIConfig(regex=True))
    )
    messages = [{"role": "user", "content": "call me at 13800138000 or email a@b.com"}]
    pii = await strat.detect_pii(messages)
    assert pii.emails or pii.phones  # detected something
    redacted, mapping = await strat.redact(messages, pii)
    assert "13800138000" not in redacted[0]["content"]
    assert mapping.tokens  # have restorable tokens
