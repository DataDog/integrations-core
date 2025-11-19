# Agent Check: Lustre

## Overview

This check monitors [Lustre][1] through the Datadog Agent.

Lustre is a high-performance distributed file system commonly used in high-performance computing (HPC) environments. This integration provides comprehensive monitoring of Lustre cluster performance, health, and operations across all node types: clients, metadata servers (MDS), and object storage servers (OSS).

The Datadog Agent can collect many metrics from Lustre clusters, including:

- **Device Health**: Monitor the status and health of all Lustre devices and targets
- **Job Statistics**: Track per-job I/O operations, latency, and throughput on MDS and OSS nodes
- **Network Statistics**: Monitor LNET performance including local and peer network interface metrics
- **General Performance**: Collect detailed statistics on file system operations, locks, and client activities
- **Changelog Events**: Capture filesystem change events for audit and analysis (client nodes only)


**Minimum Agent version:** 7.69.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The Lustre check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

1. Edit the `lustre.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Lustre performance data. See the [sample lustre.d/conf.yaml][4] for all available configuration options.

2. Add the dd-agent user to the sudoers file to allow it to run Lustre commands without a password. Edit the sudoers file with `visudo` and add:

   ```bash
   dd-agent ALL=(ALL) NOPASSWD: /path/to/lctl, /path/to/lnetctl, /path/to/lfs
   ```


**Note**: The Datadog Agent must have sufficient privileges to execute Lustre commands (lctl, lnetctl, lfs). This typically requires running as root or with appropriate sudo permissions.

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `lustre` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Lustre integration does not include any events.

### Logs

On *client nodes* the Lustre integration can collect changelog events as structured logs. These logs contain:

- `operation_type`: The type of filesystem operation
- `timestamp`: When the operation occurred  
- `flags`: Operation flags
- `message`: Detailed operation information

**Important**: Changelog users must be registered for changelogs to be collected. Use the `lctl changelog_register` command to register changelog users. (see Lustre manual [here][9])

To collect Lustre changelogs:

1. Enable logs in your `datadog.yaml` file:

```yaml
   logs_enabled: true
```

2. Uncomment and edit the logs configuration block in your `lustre.d/conf.yaml` file. For example:

```yaml
   logs:
     - type: integration
       source: lustre
       service: lustre
``` 

3. Enable changelog collection in the `lustre.d/conf.yaml` file.

```yaml
   enable_changelogs: true
```

### Service Checks

The Lustre integration does not include any service checks.

## Troubleshooting

### Permissions

The Lustre integration requires elevated privileges to run Lustre commands. Ensure the Datadog Agent is running with appropriate permissions:

```bash
# Check if the Agent user can run Lustre commands
sudo -u dd-agent lctl dl
sudo -u dd-agent sudo lnetctl net show
```

### Node Type Detection

If the integration cannot automatically detect the node type, specify it explicitly in the configuration:

```yaml
instances:
  - node_type: client  # or 'mds' or 'oss'
```

### Missing Metrics

If expected metrics are not appearing:

1. Verify the Lustre services are running and accessible
2. Check that the specified filesystem names match actual filesystems
3. Ensure the Agent has permission to read Lustre parameters
4. Enable debug logging to see detailed error messages

### Changelog Registration

For changelog collection on client nodes, ensure changelog users are registered:

```bash
# Register a changelog user
sudo lctl changelog_register

# List registered changelog users  
sudo lctl get_param mdd.*.changelog_users
```

Need help? Contact [Datadog support][8].

[1]: https://www.lustre.org/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/lustre/datadog_checks/lustre/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/lustre/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://doc.lustre.org/lustre_manual.xhtml#idm140276013629712
