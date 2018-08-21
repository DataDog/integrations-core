# HTTP Integration

## Overview

Monitor the up/down status of local or remote HTTP endpoints. The HTTP check can detect bad response codes (e.g. 404), identify soon-to-expire SSL certificates, search responses for specific text, and much more. The check also submits HTTP response times as a metric.

## Setup

### Installation

The HTTP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on the servers from which you will probe your HTTP sites. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you may want to run this status-oriented check from hosts that do not run the monitored sites.

### Configuration

Edit the `http_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][10]. See the [sample http_check.d/conf.yaml][2] for all available configuration options:

```
init_config:

instances:
  - name: Example website
    url: https://example.com/
    # disable_ssl_validation: false      # default is true, so set false to check SSL validation
    # ca_certs: /path/to/ca/file         # e.g. /etc/ssl/certs/ca-certificates.crt
    # check_certificate_expiration: true # default is true
    # days_warning: 28                   # default 14
    # days_critical: 14                  # default 7
    # timeout: 3                         # in seconds. Default is 10.
  - name: Example website (staging)
    url: http://staging.example.com/
```

The HTTP check has more configuration options than many checks - many more than are shown above. Most options are opt-in, e.g. the Agent will not check SSL validation unless you configure the requisite options. Notably, the Agent _will_ check for soon-to-expire SSL certificates by default.

See the [sample http_check.d/conf.yaml][2] for a full list and description of available options, here is a list of them:

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
| `disable_ssl_validation`         | This setting will skip SSL certificate validation and is enabled by default. If you require SSL certificate validation, set this to `false`. This option is only used when gathering the response time/aliveness from the specified endpoint. Note this setting doesn't apply to the `check_certificate_expiration` option. |
| `ignore_ssl_warning`             | When SSL certificate validation is enabled (see setting above), this setting will allow you to disable security warnings.                                                                                                                                                                                                   |
| `ca_certs`                       | This setting will allow you to override the default certificate path as specified in `init_config`                                                                                                                                                                                                                          |
| `check_certificate_expiration`   | When `check_certificate_expiration` is enabled, the service check will check the expiration date of the SSL certificate. Note that this will cause the SSL certificate to be validated, regardless of the value of the `disable_ssl_validation` setting.                                                                    |
| `days_warning` & `days_critical` | When `check_certificate_expiration` is enabled, these settings will raise a warning or critical alert when the SSL certificate is within the specified number of days from expiration.                                                                                                                                      |
| `check_hostname`                 | When `check_certificate_expiration` is enabled, this setting will raise a warning if the hostname on the SSL certificate does not match the host of the given URL.                                                                                                                                                          |
| `ssl_server_name`                | When `check_certificate_expiration` is enabled, this setting specifies the hostname of the service to connect to and it also overrides the host to match with if check_hostname is enabled.                                                                                                                                 |
| `headers`                        | This parameter allows you to send additional headers with the request. Please see the [example YAML file](https://github.com/DataDog/integrations-core/blob/master/http_check/datadog_checks/http_check/data/conf.yaml.example) for additional information and caveats.                                                     |
| `skip_proxy`                     | If set, the check will bypass proxy settings and attempt to reach the check url directly. This defaults to `false`.                                                                                                                                                                                                         |
| `allow_redirects`                | This setting allows the service check to follow HTTP redirects and defaults to `true`.                                                                                                                                                                                                                                      |
| `tags`                           | A list of arbitrary tags that will be associated with the check. For more information about tags, please see our [Guide to tagging][3] and blog post, [The power of tagged metrics][4]                                                                                                                                      |


When you have finished configuring `http_check.d/conf.yaml`, [restart the Agent][5] to begin sending HTTP service checks and response times to Datadog.

### Validation

[Run the Agent's `status` subcommand][6] and look for `http_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The HTTP check does not include any events at this time.

### Service Checks

To create alert conditions on these service checks in Datadog, select 'Network' on the [Create Monitor][8] page, not 'Integration'.

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
Need help? Contact [Datadog Support][9].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/http_check/datadog_checks/http_check/data/conf.yaml.example
[3]: https://docs.datadoghq.com/getting_started/tagging/
[4]: https://www.datadoghq.com/blog/the-power-of-tagged-metrics/
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/http_check/metadata.csv
[8]: https://app.datadoghq.com/monitors#/create
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
