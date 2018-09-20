# Pivotal Container Service Integration

## Overview

This integration monitors [Pivotal Container Service][1] clusters.

## Setup

Since Datadog already integrates with Kubernetes, it is ready-made to monitor PKS.

### Metric Collection

Monitoring PKS requires that you set up the Datadog integration for [Kubernetes][2].

### Log Collection

**Available for Agent >6.0**

The setup is exactly the same as for Kubernetes.
To start collecting logs from all your containers, use your Datadog Agent [environment variables][3].

You can also take advantage of DaemonSets to [automatically deploy the Datadog Agent on all your nodes][4].

Follow the [container log collection steps][5] to learn more about those environment variables and discover more advanced setup options.

## Troubleshooting

Need help? Contact [Datadog Support][6].


[1]: https://pivotal.io/platform/pivotal-container-service
[2]: https://docs.datadoghq.com/integrations/kubernetes/
[3]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#log-collection-setup
[4]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#container-installation
[5]: https://docs.datadoghq.com/logs/log_collection/docker/#option-2-container-installation
[6]: https://docs.datadoghq.com/help/
