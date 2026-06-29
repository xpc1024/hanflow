from hanflow.models.providers.anthropic import AnthropicProvider
from hanflow.models.providers.deepseek import DeepSeekProvider
from hanflow.models.providers.glm import GLMProvider
from hanflow.models.providers.vllm import VLLMProvider


def test_cloud_providers_not_local():
    assert AnthropicProvider().is_local is False
    assert DeepSeekProvider().is_local is False
    assert GLMProvider().is_local is False


def test_vllm_is_local():
    assert VLLMProvider().is_local is True


def test_providers_list_models():
    assert AnthropicProvider().supported_models()
    assert GLMProvider().supported_models()
    assert DeepSeekProvider().supported_models()
