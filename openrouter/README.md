# OpenRouter

## Overview

[OpenRouter][1] is a unified API gateway that routes large language model (LLM) requests across many model providers.

This integration collects per-request usage and cost records from the OpenRouter analytics API, including cost in USD, token counts, model, provider, API key, workspace, organization member, end user, and session. Use this data to attribute LLM spend and usage across your organization.

## Setup

### Generate a management key in OpenRouter

1. Log in to [OpenRouter][1].
2. In your organization settings, create a management key.
3. Copy the management key.

### Connect your OpenRouter organization to Datadog

1. Add your OpenRouter management key.

    | OpenRouter Parameters | Description                                      |
    |-----------------------|--------------------------------------------------|
    | Management Key        | The management key generated in the steps above. |

2. Click the **Save** button to save your settings.

## Data Collected

### Metrics

The OpenRouter integration does not include any metrics.

### Events

The OpenRouter integration does not include any events.

### Service Checks

The OpenRouter integration does not include any service checks.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://openrouter.ai/
[2]: https://docs.datadoghq.com/help/
