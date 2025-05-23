# Agent Check: Windows Certificate Store

## Overview

This check monitors the Local Machine certificates in the [Windows Certificate Store][1] for ceritificate expiration.

## Setup

### Installation

The Windows Certificate Store check is included in the [Datadog Agent][2] package. Please see the next section to configure the check.

### Configuration

Edit the `windows_certificate.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][10]. See the [sample windows_certificate.d/conf.yaml][4] for all available configuration options. When you are done editing the configuration file, [restart the Agent][5] to load the new configuration.

The check can monitor the expiration of all certiificates in a given store or selectively monitor a few certificates by a given list of strings matching with the certificate subjects. Enter the store name as found in `HKEY_LOCAL_MACHINE\Software\Microsoft\SystemCertificates`.

This example configuration monitors all certificates in the local machine's `ROOT` store:

```yaml
instances:
  - certificate_store: ROOT
```
This example configuraiton monitors ceritificates in `ROOT` that have `microsoft` or `verisign` in the subject:
```yaml
instances:
  - certificate_store: ROOT
    certificate_subjects:
      - microsoft
      - verisign
```
The parameters `days_warning` and `days_critical` are used to specify the number of days before certificate expiration from which the service check `windows_certificate.cert_expiration` begins emitting WARNING/CRITICAL. In the below example the service check will emit a WARNING when a certificate is 10 days from expiring and CRITICAL when it is 5 days away from expiring:
```yaml
instances:
  - certificate_store: ROOT
    certificate_subjects:
      - microsoft
      - verisign
    days_warning: 10
    days_critical: 5
```

### Validation

[Run the Agent's status subcommand][6] and look for `windows_certificate` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The windows_certificate integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/certificate-stores
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/windows_certificate.d/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/windows_certificate/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/windows_certificate/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
