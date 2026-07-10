# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from importlib.util import find_spec
from inspect import Signature, signature

from ddev.ai.agent.provider import AgentProvider, AnthropicProvider
from ddev.ai.agent.registry import AgentProviderRegistry


def test_provider_components_have_focused_modules():
    assert find_spec("ddev.ai.agent.provider") is not None
    assert find_spec("ddev.ai.agent.registry") is not None


def test_provider_methods_omit_none_return_annotations():
    methods = (
        AgentProvider.validate_config,
        AnthropicProvider.__init__,
        AnthropicProvider.validate_config,
        AgentProviderRegistry.__init__,
        AgentProviderRegistry.register,
        AgentProviderRegistry.validate_config,
    )

    for method in methods:
        assert signature(method).return_annotation is Signature.empty
