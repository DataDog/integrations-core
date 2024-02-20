# Agent Check: Openstack Controller

## Overview

**Note**: This integration only applies to OpenStack v13+. If you are looking to collect metrics from OpenStack v12 and below, use the [OpenStack integration][1].

This check monitors [OpenStack][2] from the controller node.

## Setup

### Installation

The OpenStack Controller check is included in the [Datadog Agent][3] package, so you do not need to install anything else on your server.

### Configuration

The OpenStack Controller integration is designed to collect information from all compute nodes and the servers running it. The integration should be run from a single Agent to monitor your OpenStack environment, and can be deployed on your controller node or an adjacent server that has access to the Keystone, Nova, Neutron, Cinder, Ironic, and Octavia endpoints.

#### Prepare OpenStack

Create a `datadog` user that is used in your `openstack_controller.d/conf.yaml` file. This user requires admin read-only permissions across your environment so that it can be run from a single node and read high level system information about all nodes and servers.

#### Agent configuration

1. Edit the `openstack_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your OpenStack Controller performance data. See the [sample openstack_controller.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     - keystone_server_url: "<AUTH_URL>"
       password: "<PASSWORD>"
       username: "<USER_NAME>"
       domain_id: "<DOMAIN_ID>"
   ```

2. [Restart the Agent][5]

**Note**: If you are upgrading the integration to v6.0.0 or later from v5.0.0 or older, you need to enable the `use_legacy_check_version` flag to use newer features. You may also need to make changes to your configuration to maintain compatibility. See the [sample openstack controller.d/conf.yaml][4] for details.  

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, you can enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `openstack_controller.d/conf.yaml` file to start collecting your Openstack logs:

   ```yaml
   logs:
     - type: file
       path: "<LOG_FILE_PATH>"
       source: openstack
   ```

    Change the `path` parameter value and configure them for your environment. See the [sample openstack_controller.d/conf.yaml][4] for all available configuration options.
   

### Validation

[Run the Agent's `status` subcommand][6] and look for `openstack_controller` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

OpenStack Controller does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor your OpenStack components with Datadog][10]


[1]: https://docs.datadoghq.com/integrations/openstack/
[2]: https://www.openstack.org
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/datadog_checks/openstack_controller/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/openstack-controller-integration/
