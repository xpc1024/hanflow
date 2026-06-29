from hanflow.models.providers.base import ModelProvider

from tests.models.conftest import FakeProvider


def test_fake_provider_satisfies_protocol():
    p = FakeProvider("cloud", is_local=False)
    assert isinstance(p, ModelProvider)


def test_is_local_flag():
    assert FakeProvider("local", is_local=True).is_local is True
    assert FakeProvider("cloud", is_local=False).is_local is False


def test_supported_models():
    p = FakeProvider("cloud", models=["a", "b"])
    assert set(p.supported_models()) == {"a", "b"}
