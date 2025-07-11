# Airbyte OTel Dashboard & Monitor Assets

This folder contains templates and mapping resources to help port Airbyte Datadog dashboards and monitors to use OpenTelemetry (OTel) metrics, as exposed by Airbyte's new OTel integration.

## Structure

- `dashboards/airbyte_otel_overview.json`: Template Datadog dashboard using OTel metric names and tags. Update queries as needed for your deployment.
- `monitors/airbyte_otel_long_running_jobs.json`: Template Datadog monitor for long-running jobs using OTel metrics.
- `dashboards/airbyte_otel_mapping.csv`: Mapping table from legacy Datadog Airbyte metrics to OTel metrics, with notes on gaps and translation.
- `upload_airbyte_otel_assets.py`: Python script to upload dashboards and monitors to Datadog (see below).

## How to Use

1. **Review the mapping CSV** to understand which Datadog metrics have direct OTel equivalents and which do not.
2. **Edit the dashboard and monitor JSON files** to use the correct OTel metric names and tags for your environment. See [Airbyte OTel metrics documentation](https://docs.airbyte.com/platform/operator-guides/collecting-metrics#available-metrics).
3. **Upload to Datadog** using the provided script (see below).

## Uploading to Datadog

A Python script (`upload_airbyte_otel_assets.py`) is provided to upload dashboards and monitors. It uses `uv` for package management and requires your Datadog API and APP keys as environment variables:

```sh
export DD_API_KEY=your_api_key
export DD_APP_KEY=your_app_key
uv run python upload_airbyte_otel_assets.py
```

## References
- [Airbyte OTel Metrics Documentation](https://docs.airbyte.com/platform/operator-guides/collecting-metrics#available-metrics)
- [Datadog Dashboard API](https://docs.datadoghq.com/api/latest/dashboards/)
- [Datadog Monitors API](https://docs.datadoghq.com/api/latest/monitors/)

---

This folder is a starting point for your migration. Update and extend as needed for your use case.
