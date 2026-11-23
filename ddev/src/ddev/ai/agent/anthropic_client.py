# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio

import anthropic

from ddev.ai.agent.exceptions import AgentConnectionError, AgentError, ModelAccessError
from ddev.ai.agent.provider import ModelAccessCheck
from ddev.ai.errors import RunAbortError
from ddev.ai.model_catalog import ANTHROPIC, ANTHROPIC_MESSAGES, ResolvedModel
from ddev.ai.runtime.connections import DirectAuthScheme, RouteConnection

CHECK_TIMEOUT = 15
DIRECT_AUTH = DirectAuthScheme("Authorization", "Bearer ")
# Skip SDK credential discovery and satisfy header validation before the transport runs.
SDK_AUTH_DISABLED = "togo-transport-auth"


def messages_client(connection: RouteConnection) -> anthropic.AsyncAnthropic:
    """Build a Messages client whose transport owns authentication."""
    endpoint = connection.base_url(ANTHROPIC_MESSAGES)
    # The SDK appends /v1/messages itself.
    return anthropic.AsyncAnthropic(
        api_key=SDK_AUTH_DISABLED,
        base_url=None if endpoint is None else endpoint.removesuffix("/v1"),
        http_client=anthropic.DefaultAsyncHttpxClient(
            transport=connection.transport(ANTHROPIC, direct_auth=DIRECT_AUTH),
            follow_redirects=False,
            trust_env=False,
        ),
        max_retries=connection.max_retries,
    )


async def check_messages_access(client: anthropic.AsyncAnthropic, model: ResolvedModel) -> ModelAccessCheck:
    """Verify Messages access with a one-token request and report failures without response bodies."""
    requested_model = model.binding.model
    try:
        async with asyncio.timeout(CHECK_TIMEOUT):
            response = await client.messages.with_raw_response.create(
                model=requested_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
                extra_headers=dict(model.binding.headers),
            )
            message = await response.parse()
    except (TimeoutError, anthropic.APITimeoutError):
        raise AgentConnectionError("Model access check timed out.", timed_out=True) from None
    except anthropic.APIConnectionError as error:
        if isinstance(error.__cause__, (AgentError, RunAbortError)):
            raise error.__cause__ from None
        raise AgentConnectionError("Model access check could not connect.") from None
    except anthropic.APIStatusError as error:
        raise ModelAccessError(error.status_code) from None
    except anthropic.APIError:
        raise ModelAccessError() from None
    return ModelAccessCheck(
        response.status_code,
        requested_model,
        message.model in (requested_model, requested_model.partition("/")[2]),
    )
