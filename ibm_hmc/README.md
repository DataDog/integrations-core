# IBM HMC

## Overview

The IBM HMC check collects performance metrics from POWER systems managed by an
IBM Hardware Management Console (HMC).

The check connects to the HMC appliance over SSH and runs `lslparutil` on it,
so it can run on any host that can reach the HMC: an AIX LPAR, a Linux box, or
anywhere else the Datadog Agent runs.

**This check is only shipped with the Agent for AIX.**

Metrics collected:

- **LPAR statistics** (`ibm_hmc.lpar.*`): per-partition processor and memory usage,
  such as entitled cycles, capped/uncapped cycles, and current memory.
- **Shared processor pool statistics** (`ibm_hmc.pool.*`, `ibm_hmc.procpool.*`): pool
  cycles and available/configurable processor units.
- **Memory pool statistics** (`ibm_hmc.mempool.*`): shared memory pool allocation
  and firmware memory.
- **Managed system statistics** (`ibm_hmc.sys.*`): available and configurable system
  memory.
- **HMC appliance statistics** (`ibm_hmc.system.memory.*`): memory and swap usage
  of the HMC appliance itself, from `/proc/meminfo` and `monhmc`.

## Setup

### Installation

The IBM HMC check is included in the [Datadog Agent][1] package for AIX. No additional
installation is needed on the HMC.

### Configuration

1. Edit the `ibm_hmc.d/conf.yaml` file in your Agent's `conf.d/` directory.
   See the [sample ibm_hmc.d/conf.yaml][2] for all available configuration options.

2. Configure SSH access to the HMC. The recommended setup is an account with
   a read-only role (for example `hscroot`) and either a password or a private
   key:

   ```yaml
   instances:
     - host: hmc.example.com
       username: hscroot
       password: <PASSWORD>
   ```

   If the Agent user's known hosts file does not contain the HMC's host key
   yet, add it with `ssh-keyscan <HMC HOSTNAME> >> ~/.ssh/known_hosts`, run as
   the Agent user (`dd-agent` by default). The check reads that user's known
   hosts and rejects connections to hosts with unknown keys.

3. [Restart the Agent][3].

#### Collection interval

The HMC only produces new `lslparutil` samples at its own configured sample
rate (often 60 seconds or more). The check reads that rate per managed system
and skips subsystems whose sample rate has not elapsed, so the default
collection interval works but collects each sample as soon as it is available.
Set `min_collection_interval` to the sample rate to avoid polling more often
than needed.

#### Clock synchronization

The `lslparutil` start options are expressed in HMC-local time, so the check
queries the HMC's clock for its first collection window and keeps track of
the HMC-side time of the last collected sample afterwards. The Agent's time
zone and clock skew therefore do not affect collection; only keep the HMC
itself reasonably in sync (NTP) so samples are produced with sane timestamps.

### Validation

Run the [Agent's status subcommand][4] and look for `ibm_hmc` under the Checks
section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.
The `ibm_hmc.system.memory.*` metrics come from the HMC's `/proc/meminfo`, so the
exact set depends on the HMC firmware version.

### Service Checks

The IBM HMC check does not include any service checks.

Connectivity is reported with the `ibm_hmc.can_connect` metric instead: `1`
when the Agent can connect to the HMC over SSH, `0` otherwise. Monitor it with
for example `max(last_5m):avg:ibm_hmc.can_connect{*} by {hmc-instance} < 1`.

### Events

The IBM HMC check does not include any events.

## Support

Need help? Contact [Datadog support][6].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://github.com/DataDog/integrations-core/blob/master/ibm_hmc/datadog_checks/ibm_hmc/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_hmc/metadata.csv
[6]: https://docs.datadoghq.com/help/
