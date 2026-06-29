from hanflow.models.strategies.base import RoutingRequest
from hanflow.models.strategies.cost import CostStrategy
from hanflow.models.strategies.fallback import FallbackStrategy
from hanflow.models.strategies.role import RoleStrategy
from hanflow.models.strategies.static import StaticStrategy
from hanflow.models.strategies.task import TaskStrategy

from tests.models.conftest import FakeProvider


def _providers():
    return {
        "cloud": FakeProvider("cloud", models=["strong", "fast"]),
        "local": FakeProvider("local", is_local=True, models=["local-m"]),
    }


def test_static_returns_prefer():
    s = StaticStrategy()
    req = RoutingRequest(messages=[], prefer=("cloud", "fast"))
    cands = s.candidates(req, _providers())
    assert cands[0].provider == "cloud"
    assert cands[0].model == "fast"
    assert "static" in cands[0].reason


def test_static_no_prefer_returns_empty():
    assert StaticStrategy().candidates(RoutingRequest(messages=[]), _providers()) == []


def test_role_maps_role_to_model():
    s = RoleStrategy(roles={"planner": ("cloud", "strong"), "coder": ("cloud", "fast")})
    req = RoutingRequest(messages=[], role="planner")
    cands = s.candidates(req, _providers())
    assert cands[0].model == "strong"


def test_task_maps_task_type():
    s = TaskStrategy(tasks={"coding": ("cloud", "fast"), "reasoning": ("cloud", "strong")})
    req = RoutingRequest(messages=[], task_type="coding")
    assert s.candidates(req, _providers())[0].model == "fast"


def test_cost_picks_cheaper_when_budget_low():
    s = CostStrategy(
        tiers=[
            {"budget_above": 0.5, "use": ("cloud", "strong")},
            {"budget_above": 0.0, "use": ("cloud", "fast")},
        ]
    )
    req = RoutingRequest(messages=[], run_budget_remaining=0.3)
    assert s.candidates(req, _providers())[0].model == "fast"
    req2 = RoutingRequest(messages=[], run_budget_remaining=0.9)
    assert s.candidates(req2, _providers())[0].model == "strong"


def test_fallback_chain_exposed():
    chain = [("cloud", "strong"), ("local", "local-m")]
    s = FallbackStrategy(chain=chain)
    assert s.candidates(RoutingRequest(messages=[]), _providers()) == []
    assert s.chain[0].provider == "cloud"
    assert s.chain[1].provider == "local"
