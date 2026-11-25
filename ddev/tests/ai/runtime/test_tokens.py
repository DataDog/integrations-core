# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.runtime.tokens import DirectTokenProducer


@pytest.mark.parametrize("rejected", [False, True], ids=["reused", "rejected"])
async def test_direct_token_producer_keeps_the_key_for_each_provider_for_the_run(rejected):
    keys = {"provider-a": "secret-a", "provider-b": "secret-b"}
    producer = DirectTokenProducer({name: lambda name=name: keys[name] for name in keys})

    assert producer.has_key("provider-a")
    keys["provider-a"] = "rotated-a"
    if rejected:
        producer.reject("secret-a")
    assert await producer.token_for("provider-a") == "secret-a"
    assert await producer.token_for("provider-b") == "secret-b"


@pytest.mark.parametrize("key", [None, "", " "])
async def test_direct_token_producer_refuses_missing_or_blank_keys(key):
    producer = DirectTokenProducer({"provider-a": lambda: "secret-a", "provider-b": lambda: key})

    with pytest.raises(ResourceUnavailableError, match="No direct credential is configured for provider-b"):
        await producer.token_for("provider-b")
