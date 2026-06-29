import pytest

from hanflow.core.errors import PrivacyViolationError
from hanflow.models.governance import GovernanceConfig, GovernanceLayer
from hanflow.models.privacy import PIIConfig, PrivacyConfig, PrivacyStrategy
from hanflow.models.providers.fake import FakeProvider
from hanflow.models.router import ModelRouter
from hanflow.models.strategies.fallback import FallbackStrategy
from hanflow.models.strategies.role import RoleStrategy
from hanflow.observability.trace import NullTraceExporter


def _providers():
    return {
        "cloud": FakeProvider("cloud", is_local=False, models=["strong", "fast"]),
        "local": FakeProvider("local", is_local=True, models=["local-m"]),
    }


def _router(providers, strategies):
    return ModelRouter(
        providers=providers,
        strategies=strategies,
        governance=GovernanceLayer(GovernanceConfig()),
        trace=NullTraceExporter(),
        default_model=("cloud", "strong"),
    )


@pytest.mark.asyncio
async def test_privacy_vetoes_role_preference():
    """Even with role=planner→strong(cloud), confidential data must go local."""
    providers = _providers()
    router = _router(
        providers,
        [
            PrivacyStrategy(
                PrivacyConfig(local_providers=["local"], pii_detection=PIIConfig(regex=True))
            ),
            RoleStrategy(roles={"planner": ("cloud", "strong")}),
        ],
    )
    resp = await router.complete(
        [{"role": "user", "content": "secret"}], role="planner", sensitivity="confidential"
    )
    assert resp.provider == "local"


@pytest.mark.asyncio
async def test_role_wins_over_default():
    providers = _providers()
    router = _router(providers, [RoleStrategy(roles={"planner": ("cloud", "strong")})])
    resp = await router.complete([{"role": "user", "content": "hi"}], role="planner")
    assert resp.model_used == "strong"


@pytest.mark.asyncio
async def test_fallback_after_cloud_failure():
    from hanflow.core.errors import ModelTimeoutError

    providers = _providers()
    providers["cloud"].fail_with = ModelTimeoutError("down")
    router = _router(
        providers,
        [FallbackStrategy(chain=[("cloud", "strong"), ("local", "local-m")])],
    )
    resp = await router.complete([{"role": "user", "content": "hi"}])
    assert resp.provider == "local"


@pytest.mark.asyncio
async def test_hard_privacy_raises_when_no_local():
    providers = {"cloud": FakeProvider("cloud", is_local=False)}
    router = _router(
        providers,
        [
            PrivacyStrategy(
                PrivacyConfig(
                    local_providers=["local"], enforce="hard", pii_detection=PIIConfig(regex=True)
                )
            )
        ],
    )
    with pytest.raises(PrivacyViolationError):
        await router.complete([{"role": "user", "content": "secret"}], sensitivity="restricted")
