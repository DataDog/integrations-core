# Agent Check: InterSystems IRIS

## Overview

This check monitors [InterSystems IRIS][1] through the Datadog Agent. To learn more, see the [InterSystems IRIS integration documentation][2].

## Setup

See the [InterSystems IRIS integration documentation][2] for setup and configuration instructions.

### Log collection

_Available for Agent versions >6.0_

For containerized environments, follow the instructions on the [Kubernetes Log Collection][4] or [Docker Log Collection][5] pages.

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `intersystems_iris.d/conf.yaml` file to start collecting your InterSystems IRIS logs:

   ```yaml
     logs:
       - type: file
         path: /usr/irissys/mgr/messages.log
         source: intersystems_iris
         service: <SERVICE_NAME>
         log_processing_rules:
            - type: multi_line
              name: new_log_start_with_date
              # pattern to match: 08/17/26-13:18:52:293
              pattern: \d{2}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2}
   ```

## Support

Need help? Contact [Datadog support][3].

[1]: https://www.intersystems.com/products/intersystems-iris/
[2]: https://docs.datadoghq.com/integrations/intersystems_iris/
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/containers/kubernetes/log/
[5]: https://docs.datadoghq.com/containers/docker/log/
