**Step 1: Generate an OpenAI API key**

An **admin-scoped** API key is required to collect usage metrics and Cloud Cost Management (CCM) cost data. Project-scoped keys cannot collect this data.

1. Log in to your [OpenAI account][1].
2. Go to the [Admin keys page][2], or open **API keys** under **Organization settings** and select the **Admin keys** tab.
3. Click **Create a new secret key**.
4. Copy the generated admin API key.

Admin keys cannot call model endpoints, so they cannot run LLM evaluations. To use a key for evaluations in LLM Observability, add a standard API key on the **LLM Evaluations** interface.

**Step 2: Create the Datadog integration**

1. Enter a name for the account.
2. Paste the admin API key into the **Admin API Key** field below.
3. Optionally, add a comma-separated list of tags applied to the metrics collected for this account.
4. Optionally, enable **Collect cost data to view in Cloud Cost Management**. Cost data appears in [Cloud Cost Management][3] within 24 hours.

### Troubleshooting

If usage metrics or cost data are missing, confirm the API key is admin-scoped. Without an admin-scoped key, the `audio_speeches`, `audio_transcriptions`, `code_interpreter_sessions`, `completions`, `embeddings`, `images`, `moderations`, and `vector_stores` metrics are not collected and CCM cost data is unavailable.

### Validation

Once the integration is installed, query `openai.completions.*` metrics in Datadog to confirm data is arriving.

[1]: https://platform.openai.com/
[2]: https://platform.openai.com/settings/organization/admin-keys
[3]: https://docs.datadoghq.com/cloud_cost_management/
