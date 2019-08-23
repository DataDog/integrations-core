# HTTP Integration

## Overview

Monitor the up/down status of local or remote HTTP endpoints. The HTTP check can detect bad response codes (e.g. 404), identify soon-to-expire SSL certificates, search responses for specific text, and much more. The check also submits HTTP response times as a metric.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

The HTTP check is included in the [Datadog Agent][2] package, so you don't need to install anything else on the servers from which you will probe your HTTP sites. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you may want to run this status-oriented check from hosts that do not run the monitored sites.

### Configuration

Edit the `http_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample http_check.d/conf.yaml][4] for all available configuration options:

```
init_config:

instances:
  - name: Example website
    url: https://example.com/
    # tls_verify: true      # default is true, so set false to ignore SSL validation
    # tls_ca_cert: /path/to/ca/file         # e.g. /etc/ssl/certs/ca-certificates.crt
    # check_certificate_expiration: true # default is true
    # days_warning: 28                   # default 14
    # days_critical: 14                  # default 7
    # timeout: 3                         # in seconds. Default is 10.
  - name: Example website (staging)
    url: http://staging.example.com/
```

The HTTP check has more configuration options than many checks - many more than are shown above. Most options are opt-in, e.g. the Agent will not check SSL validation unless you configure the requisite options. Notably, the Agent _will_ check for soon-to-expire SSL certificates by default.

This check runs on every run of the Agent collector, which defaults to every 15 seconds. To set a custom run frequency for this check, refer to the [collection interval][5] section of the custom check documentation.

See the [sample http_check.d/conf.yaml][4] for a full list and description of available options, here is a list of them:

| Setting                          | Description                                                                                                                                                                                                                                                                                                                 |
| ---                              | ---                                                                                                                                                                                                                                                                                                                         |
| `name`                           | The name associated with this instance/URL. This will be presented as a tag on Service Checks. Note: This name tag will have any spaces or dashes converted to underscores.                                                                                                                                                 |
| `url`                            | The URL to test.                                                                                                                                                                                                                                                                                                            |
| `timeout`                        | The time in seconds to allow for a response.                                                                                                                                                                                                                                                                                |
| `method`                         | The HTTP method. This setting defaults to GET, though many other HTTP methods are supported, including POST and PUT.                                                                                                                                                                                                        |
| `data`                           | The data option is only available when using the POST method. Data should be included as key-value pairs and will be sent in the body of the request.                                                                                                                                                                       |
| `content_match`                  | A string or Python regular expression. The HTTP check will search for this value in the response and will report as DOWN if the string or expression is not found.                                                                                                                                                          |
| `reverse_content_match`          | When true, reverses the behavior of the `content_match` option, i.e. the HTTP check will report as DOWN if the string or expression in `content_match` IS found. (default is false)                                                                                                                                         |
| `username` & `password`          | If your service uses basic authentication, you can provide the username and password here.                                                                                                                                                                                                                                  |
| `http_response_status_code`      | A string or Python regular expression for an HTTP status code. This check will report DOWN for any status code that does not match. This defaults to 1xx, 2xx and 3xx HTTP status codes. For example: `401` or `4\d\d`.                                                                                                     |
| `include_content`                | When set to `true`, the check will include the first 200 characters of the HTTP response body in notifications. The default value is `false`.                                                                                                                                                                               |
| `collect_response_time`          | By default, the check will collect the response time (in seconds) as the metric `network.http.response_time`. To disable, set this value to `false`.                                                                                                                                                                        |
| `tls_verify`         | This setting will require SSL certificate validation and is enabled by default. If you want to skip SSL certificate validation, set this to `false`. This option is only used when gathering the response time/aliveness from the specified endpoint. Note this setting doesn't apply to the `check_certificate_expiration` option. |
| `tls_ignore_warning`             | When SSL certificate validation is enabled (see setting above), this setting will allow you to disable security warnings.                                                                                                                                                                                                   |
| `tls_ca_cert`                       | This setting will allow you to override the default certificate path as specified in `init_config`                                                                                                                                                                                                                          |
| `check_certificate_expiration`   | When `check_certificate_expiration` is enabled, the service check will check the expiration date of the SSL certificate. Note that this will cause the SSL certificate to be validated, regardless of the value of the `disable_ssl_validation` setting.                                                                    |
| `days_warning` & `days_critical` | When `check_certificate_expiration` is enabled, these settings will raise a warning or critical alert when the SSL certificate is within the specified number of days from expiration.                                                                                                                                      |
| `check_hostname`                 | When `check_certificate_expiration` is enabled, this setting will raise a warning if the hostname on the SSL certificate does not match the host of the given URL.                                                                                                                                                          |
| `ssl_server_name`                | When `check_certificate_expiration` is enabled, this setting specifies the hostname of the service to connect to and it also overrides the host to match with if check_hostname is enabled.                                                                                                                                 |
| `headers`                        | This parameter allows you to send additional headers with the request. See the [example YAML file][6] for additional information and caveats.                                                     |
| `skip_proxy`                     | If set, the check will bypass proxy settings and attempt to reach the check url directly. This defaults to `false`.                                                                                                                                                                                                         |
| `allow_redirects`                | This setting allows the service check to follow HTTP redirects and defaults to `true`.                                                                                                                                                                                                                                      |
| `tags`                           | A list of arbitrary tags that will be associated with the check. For more information about tags, see our [Guide to tagging][7] and blog post, [The power of tagged metrics][8]                                                                                                                                      |


When you have finished configuring `http_check.d/conf.yaml`, [restart the Agent][9] to begin sending HTTP service checks and response times to Datadog.

### Validation

[Run the Agent's `status` subcommand][10] and look for `http_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Events

The HTTP check does not include any events.

### Service Checks

To create alert conditions on these service checks in Datadog, select 'Network' on the [Create Monitor][12] page, not 'Integration'.

**`http.can_connect`**:

Returns `DOWN` when any of the following occur:

* the request to `uri` times out
* the response code is 4xx/5xx, or it doesn't match the pattern provided in the `http_response_status_code`
* the response body does *not* contain the pattern in `content_match`
* `reverse_content_match` is true and the response body *does* contain the pattern in `content_match`
* `uri` contains `https` and `disable_ssl_validation` is false, and the SSL connection cannot be validated

Otherwise, returns `UP`.

**`http.ssl_cert`**:

The check returns:

* `DOWN` if the `uri`'s certificate has already expired
* `CRITICAL` if the `uri`'s certificate expires in less than `days_critical` days
* `WARNING` if the `uri`'s certificate expires in less than `days_warning` days

Otherwise, returns `UP`.

To disable this check, set `check_certificate_expiration` to false.

## Troubleshooting
Need help? Contact [Datadog support][13].

[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/http_check/datadog_checks/http_check/data/conf.yaml.example
[5]: https://docs.datadoghq.com/developers/write_agent_check/?tab=agentv6#collection-interval
[6]: https://github.com/DataDog/integrations-core/blob/master/http_check/datadog_checks/http_check/data/conf.yaml.example
[7]: https://docs.datadoghq.com/getting_started/tagging
[8]: https://www.datadoghq.com/blog/the-power-of-tagged-metrics
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/http_check/metadata.csv
[12]: https://app.datadoghq.com/monitors#/create
[13]: https://docs.datadoghq.com/help
