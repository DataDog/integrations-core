**Step 1: Generate an OpenAI API key**

An **admin-scoped** API key is required to collect usage metrics and Cloud Cost Management (CCM) cost data. Project-scoped keys cannot collect this data.

1. Log in to your [OpenAI account][1].
2. Go to the [Admin keys page][2], or open **API keys** under **Organization settings** and select the **Admin keys** tab.
3. Click **Create a new secret key**.
4. Copy the generated admin API key.

For LLM evaluations only, a standard API key with **write** permission for model capabilities is sufficient.

**Step 2: Create the Datadog integration**

1. Enter a name for the account.
2. Paste the API key into the **API Key** field below.
3. Optionally, add a comma-separated list of tags applied to the metrics collected for this account.
4. Under **Resources**, enable the toggles that match your use case:
   - **Collect Cost Data**: cost data appears in [Cloud Cost Management][3] within 24 hours. Requires an admin-scoped API key.
   - **Use this API key to evaluate your LLM applications**: evaluations run through this API key in LLM Observability.

### Troubleshooting

If usage metrics or cost data are missing, confirm the API key is admin-scoped. Without an admin-scoped key, the `audio_speeches`, `audio_transcriptions`, `code_interpreter_sessions`, `completions`, `embeddings`, `images`, `moderations`, and `vector_stores` metrics are not collected and CCM cost data is unavailable.

### Validation

Once the integration is installed, query `openai.api.usage.*` metrics in Datadog to confirm data is arriving.

[1]: https://platform.openai.com/
[2]: https://platform.openai.com/settings/organization/admin-keys
[3]: https://docs.datadoghq.com/cloud_cost_management/
