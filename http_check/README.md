# HTTP Integration

## Overview

Monitor the up/down status of local or remote HTTP endpoints. The HTTP check can detect bad response codes (e.g. 404), identify soon-to-expire SSL certificates, search responses for specific text, and much more. The check also submits HTTP response times as a metric.

## Setup

### Installation

The HTTP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on the servers from which you will probe your HTTP sites. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you may want to run this status-oriented check from hosts that do not run the monitored sites.

### Configuration

Edit the `http_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample http_check.d/conf.yaml][3] for all available configuration options:

```yaml
init_config:

instances:
  - name: Example website
    url: https://example.com/

  - name: Example website (staging)
    url: http://staging.example.com/
```

The HTTP check has more configuration options than many checks - many more than are shown above. Most options are opt-in, e.g. the Agent will not check SSL validation unless you configure the requisite options. Notably, the Agent _will_ check for soon-to-expire SSL certificates by default.

This check runs on every run of the Agent collector, which defaults to every 15 seconds. To set a custom run frequency for this check, refer to the [collection interval][4] section of the custom check documentation.

See the [sample http_check.d/conf.yaml][3] for a full list and description of available options, here is a list of them:

| Setting                          | Description                                                                                                                                                                                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`                           | Name of your Http check instance. This is presented as a tag on the Service Checks.                                                                                                                                                              |
| `url`                            | The URL to test.                                                                                                                                                                                                                                 |
| `timeout`                        | The time in seconds to allow for a response.                                                                                                                                                                                                     |
| `method`                         | The HTTP method to use for the check.                                                                                                                                                                                                            |
| `data`                           | Use this parameter to specify a body for a request with a POST, PUT, DELETE, or PATCH method. SOAP requests are supported if you use the POST method and supply an XML string as the data parameter.                                             |
| `headers`                        | This parameter allows you to send additional headers with the request. See the [example YAML file][3] for additional information and caveats.                                                                                                    |
| `content_match`                  | A string or Python regular expression. The HTTP check searches for this value in the response and reports as DOWN if the string or expression is not found.                                                                                      |
| `reverse_content_match`          | When `true`, reverses the behavior of the `content_match` option, i.e. the HTTP check reports as DOWN if the string or expression in `content_match` IS found. (default is `false`)                                                              |
| `username` & `password`          | If your service uses basic authentication, you can provide the username and password here.                                                                                                                                                       |
| `http_response_status_code`      | A string or Python regular expression for an HTTP status code. This check reports DOWN for any status code that does not match. This defaults to 1xx, 2xx and 3xx HTTP status codes. For example: `401` or `4\d\d`.                              |
| `include_content`                | When set to `true`, the check includes the first 200 characters of the HTTP response body in notifications. The default value is `false`.                                                                                                        |
| `collect_response_time`          | By default, the check collects the response time (in seconds) as the metric `network.http.response_time`. To disable, set this value to `false`.                                                                                                 |
| `tls_verify`                     | Instructs the check to validate the TLS certificate of services when reaching to `url`.                                                                                                                                                          |
| `tls_ignore_warning`             | If `tls_verify` is set to `true`, it disables any security warnings from the SSL connection.                                                                                                                                                     |
| `tls_ca_cert`                    | This setting allows you to override the default certificate path as specified in `init_config`                                                                                                                                                   |
| `check_certificate_expiration`   | When `check_certificate_expiration` is enabled, the service check checks the expiration date of the SSL certificate. Note that this causes the SSL certificate to be validated, regardless of the value of the `tls_verify` setting. |
| `days_warning` & `days_critical` | When `check_certificate_expiration` is enabled, these settings raise a warning or critical alert when the SSL certificate is within the specified number of days from expiration.                                                                |
| `ssl_server_name`                | When `check_certificate_expiration` is enabled, this setting specifies the hostname of the service to connect to and it also overrides the host to match with if check_hostname is enabled.                                                      |
| `check_hostname`                 | If set to `true` the check log a warning if the checked `url` hostname is different than the SSL certificate hostname.                                                                                                                           |
| `skip_proxy`                     | If set, the check will bypass proxy settings and attempt to reach the check url directly. This defaults to `false`.                                                                                                                              |
| `allow_redirects`                | This setting allows the service check to follow HTTP redirects and defaults to `true`.                                                                                                                                                           |
| `tags`                           | A list of arbitrary tags that will be associated with the check. For more information about tags, see our [Guide to tagging][5] and blog post, [The power of tagged metrics][6]                                                                  |

When you have finished configuring `http_check.d/conf.yaml`, [restart the Agent][7] to begin sending HTTP service checks and response times to Datadog.

### Validation

[Run the Agent's `status` subcommand][8] and look for `http_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

The HTTP check does not include any events.

### Service Checks

To create alert conditions on these service checks in Datadog, select 'Network' on the [Create Monitor][10] page, not 'Integration'.

**`http.can_connect`**:

Returns `DOWN` when any of the following occur:

- the request to `uri` times out
- the response code is 4xx/5xx, or it doesn't match the pattern provided in the `http_response_status_code`
- the response body does _not_ contain the pattern in `content_match`
- `reverse_content_match` is true and the response body _does_ contain the pattern in `content_match`
- `uri` contains `https` and `tls_verify` is true, and the SSL connection cannot be validated

Otherwise, returns `UP`.

**`http.ssl_cert`**:

The check returns:

- `DOWN` if the `uri`'s certificate has already expired
- `CRITICAL` if the `uri`'s certificate expires in less than `days_critical` days
- `WARNING` if the `uri`'s certificate expires in less than `days_warning` days

Otherwise, returns `UP`.

To disable this check, set `check_certificate_expiration` to false.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/http_check/datadog_checks/http_check/data/conf.yaml.example
[4]: https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
[5]: https://docs.datadoghq.com/getting_started/tagging
[6]: https://www.datadoghq.com/blog/the-power-of-tagged-metrics
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/http_check/metadata.csv
[10]: https://app.datadoghq.com/monitors#/create
[11]: https://docs.datadoghq.com/help
