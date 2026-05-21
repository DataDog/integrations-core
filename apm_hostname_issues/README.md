# APM Hostname Issues

## Overview

This dashboard helps diagnose APM hostname configuration issues. It shows services emitting hostnames that resemble pod names or empty hostnames, both of which can impact your product experience and are resolvable with proper configuration.

These issues can occur for all OpenTelemetry setups (Collector and DDOT) as well as Datadog Agent setups.

## Setup

No additional setup is required. This dashboard appears automatically when `datadog.apm.hostname_issue` metrics are detected in your environment.

To resolve hostname configuration issues, see:
- [OpenTelemetry hostname tagging][1]
- [Agent hostname configuration in containers][2]

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://docs.datadoghq.com/opentelemetry/config/hostname_tagging/?tab=host
[2]: https://docs.datadoghq.com/agent/troubleshooting/hostname_containers/?tab=datadogoperator
[3]: https://docs.datadoghq.com/help/
