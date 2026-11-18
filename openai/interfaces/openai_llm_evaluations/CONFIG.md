**Step 1: Generate an OpenAI API key**

1. Log in to your [OpenAI account][1].
2. Go to **API keys** and create a project or user key.
3. Give the key **Write** permission for model capabilities so it can call the chat completions endpoint.
4. Copy the generated API key.

Standard API keys cannot read organization usage or costs. For usage metrics and Cloud Cost Management, add an admin-scoped key on the **Usage and Cost** interface.

**Step 2: Create the Datadog integration**

1. Enter a name for the account.
2. Paste the API key into the **API Key** field below.
3. Leave **Use this API key to evaluate your LLM applications** enabled to make the key available to evaluations in LLM Observability.

### Validation

When you save the account, Datadog checks that the key can call the OpenAI chat completions endpoint.

[1]: https://platform.openai.com/
