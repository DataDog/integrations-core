# SSL Check

## Overview

This check monitors various aspects of SSL certificates.

## Setup

### Installation

The SSL check is included in the [Datadog Agent][1] package, so you do not
need to install anything else on your server. This check can monitor both local and remove SSL certificates.

### Configuration

1. Edit the `ssl.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your ssl certificate data.
   See the [sample ssl.d/conf.yaml][2] for all available configuration options.

| Setting                          | Description                                                                                                                                                                      |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                           | The name associated with this instance/URL. This will be presented as a tag on Service Checks. Note: This name tag will have any spaces or dashes converted to underscores.      |
| `url`                            | The URL to test.                                                                                                                                                                 |
| `timeout`                        | The time in seconds to allow for a response.                                                                                                                                     |
| `days_warning` & `days_critical` | These settings can be used to set a specified number of days from SSL certificate's expiration to raise a warning or critical service check status.                              |
| `check_hostname`                 | This setting will raise a warning if the hostname on the SSL certificate does not match the host of the given URL.                                                               |
| `ssl_server_name`                | This setting specifies the hostname of the service to connect to and it also overrides the host to match with if check_hostname is enabled.                                      |
| `tags`                           | A list of arbitrary tags that will be associated with the check. For more information about tags, see our [Guide to tagging][6] and blog post, [The power of tagged metrics][7]. |

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `ssl` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

To create alert conditions on these service checks in Datadog, select 'Network' on the [Create Monitor][7] page.

**`ssl_cert.can_connect`**:

- `CRITICAL` if the the request to uri times out
- `UP` otherwise

**`ssl_cert.expiration`**:

The check returns:

- `CRITICAL` if the `uri`'s certificate has expired or will expire in less than `days_critical` days
- `WARNING` if the `uri`'s certificate expires in less than `days_warning` days
- `UP` otherwise

**`ssl_cert.is_valid`**:

Checks if certificate SNI, CN, and digital signature are valid.

- `CRITICAL` if any of the uri's certificate attributes listed above are invalid
- `UP` otherwise

### Events

SSL check will post events to your Datadog Event Stream when the following certificate attributes change:

- Version Number
- Issuer Name
- Validity period
- Not Before
- Not After
- Subject name

## Troubleshooting

Need help? Contact [Datadog support][6].
[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/ssl/datadog_checks/ssl/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/ssl/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://app.datadoghq.com/monitors#/create
