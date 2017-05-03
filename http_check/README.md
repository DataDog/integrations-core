# HTTP Integration

# Overview

Monitor the up/down status of local or remote HTTP endpoints. The HTTP check can detect bad response codes (e.g. 404), identify soon-to-expire SSL certificates, search responses for specific text, and much more. The check also submits HTTP response times as a metric.

# Installation

The HTTP check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host from which you want to probe your HTTP sites. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you may want to run this status-oriented check from hosts that do not run the monitored sites.

If you need the newest version of the HTTP check, install the `dd-check-http` package; this package's check will override the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

# Configuration

Create a file `http_check.yaml` in the Agent's `conf.d` directory:

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
    # timeout: 3                         # in seconds. Default is 1.
    skip_event: true # Default is false, i.e. emit events instead of service checks. Recommend to set to true.
  - name: Example website (staging)
    url: http://staging.example.com/
    skip_event: true
```

The HTTP check has more configuration options than many checks — many more than are shown above. Most options are opt-in, e.g. the Agent will not check SSL validation unless you configure the requisite options. Notably, the Agent _will_ check for soon-to-expire SSL certificates by default.

See the [sample http_check.yaml](https://github.com/DataDog/integrations-core/blob/master/http_check/conf.yaml.example) for a full list and description of available options. There are options to send a POST (with data) instead of GET, set custom request headers, set desired response codes, and more.

When you have finished configuring `http_check.yaml`, restart the Agent to begin sending HTTP service checks and response times to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `http_check` under the Checks section:

```
  Checks
  ======
    [...]

    http_check
    ----------
      - instance #0 [WARNING]
          Warning: Skipping SSL certificate validation for https://example.com based on configuration
      - instance #1 [OK]
      - Collected 2 metrics, 0 events & 4 service checks

    [...]
```

# Troubleshooting

# Compatibility

The http_check check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/http_check/metadata.csv) for a list of metrics provided by this integration.

# Events

Older versions of the HTTP check only emitted events to reflect site status, but now the check supports service checks, too. However, events are still the default behavior. Set `skip_event` to true for all configured instances to submit service checks instead of events. The Agent will soon deprecate `skip_event`, i.e. the HTTP check's default be will only support service checks.

# Service Checks

To create alert conditions on these service checks in Datadog, select 'Network' on the [Create Monitor](https://app.datadoghq.com/monitors#/create) page, not 'Integration'.

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

* `DOWN` if the `uri`'s' certificate has already expired
* `CRITICAL` if the `uri`'s' certificate expires in less than `days_critical` days
* `WARNING` if the `uri`'s' certificate expires in less than `days_warning` days

Otherwise, returns `UP`.

To disable this check, set `check_certificate_expiration` to false.

# Further Reading
