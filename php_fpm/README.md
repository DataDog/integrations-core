# PHP-FPM Check

## Overview

The PHP-FPM check monitors the state of your FPM pool and tracks request performance.

## Setup
### Installation

The PHP-FPM check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any servers that use PHP-FPM. If you need the newest version of the check, install the `dd-check-php-fpm` package.

### Configuration

Create a file `php_fpm.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances: 
  - status_url: http://localhost/status # or whatever pm.status_path is set to in your PHP INI
    ping_url: http://localhost/ping     # or whatever ping.path is set to in your PHP INI
    ping_reply: pong                    # the reply to expect from ping; default is 'pong'
#   user: <YOUR_USERNAME>     # if the status and ping URLs require HTTP basic auth
#   password: <YOUR_PASSWORD> # if the status and ping URLs require HTTP basic auth
#   http_host: <HOST>         # if your FPM pool is only accessible via a specific HTTP vhost 
#   tags:
#     - instance:foo
```

Restart the Agent to start sending PHP-FPM metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `php_fpm` under the Checks section:

```
  Checks
  ======
    [...]

    php_fpm
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The php_fpm check is compatible with all major platforms.

## Data Collected
### Metrics 

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/php_fpm/metadata.csv) for a list of metrics provided by this check.

### Events
The php-fpm check does not include any event at this time.

### Service Checks

`php_fpm.can_ping`:

Returns CRITICAL if the Agent cannot ping PHP-FPM at the configured `ping_url`, otherwise OK.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)