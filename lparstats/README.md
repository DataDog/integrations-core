# LPARStats

## Overview

The LPARStats check collects performance metrics from IBM POWER Logical Partitions (LPARs)
running AIX by parsing the output of the `lparstat` command.

**This check is only supported on AIX.** It relies on the `lparstat` utility, which is
exclusive to IBM AIX on POWER hardware.

Metrics collected:

- **Memory statistics** (`system.lpar.memory.*`): physical memory usage, page statistics,
  I/O memory pool utilization.
- **Hypervisor call statistics** (`system.lpar.hypervisor.*`): per-call counts and latency
  for hypervisor calls. Requires root or sudo.
- **I/O memory entitlements** (`system.lpar.memory.entitlement.*`): per-pool entitlement
  and allocation data. Requires root or sudo.
- **SPURR processor utilization** (`system.lpar.spurr.*`): actual and normalized physical
  processor utilization rates.

## Setup

### Installation

The LPARStats check is included in the [Datadog Agent][1] package for AIX. No additional
installation is needed.

### Configuration

1. Edit the `lparstats.d/conf.yaml` file in your Agent's `conf.d/` directory.
   See the [sample lparstats.d/conf.yaml][2] for all available configuration options.

2. To collect hypervisor and memory entitlement metrics, the Agent must run as root, or
   the `dd-agent` user must be granted sudo access to `lparstat`:

   ```
   dd-agent ALL=(root) NOPASSWD: /usr/bin/lparstat
   ```

3. [Restart the Agent][3].

### Validation

Run the [Agent's status subcommand][4] and look for `lparstats` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Service Checks

The LPARStats check does not include any service checks.

### Events

The LPARStats check does not include any events.

## Support

Need help? Contact [Datadog support][6].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://github.com/DataDog/integrations-core/blob/master/lparstats/datadog_checks/lparstats/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/lparstats/metadata.csv
[6]: https://docs.datadoghq.com/help/
