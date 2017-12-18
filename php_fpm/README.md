# PHP-FPM Check

## Overview

The PHP-FPM check monitors the state of your FPM pool and tracks request performance.

## Setup
### Installation

The PHP-FPM check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any servers that use PHP-FPM. If you need the newest version of the check, install the `dd-check-php-fpm` package.

### Configuration

Create a file `php_fpm.yaml` in the Agent's `conf.d` directory. See the [sample php_fpm.yaml](https://github.com/DataDog/integrations-core/blob/master/php_fpm/conf.yaml.example) for all available configuration options:

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

Configuration Options:

* `status_url` (Required) - URL for the PHP FPM status page defined in the fpm pool config file (pm.status_path)
* `ping_url` (Required) - URL for the PHP FPM ping page defined in the fpm pool config file (ping.path)
* `ping_reply` (Required) - Reply from the ping_url. Unless you define a reply, it is `pong`
* `user` (Optional) - Used if you have set basic authentication on the status and ping pages
* `password` (Optional) - Used if you have set basic authentication on the status and ping pages
* `http_host` (Optional) - If your FPM pool is only accessible via a specific HTTP vhost, specify it here
Restart the Agent to start sending PHP-FPM metrics to Datadog.

### Validation

[Run the Agent's `info` subcommand](https://help.datadoghq.com/hc/en-us/articles/203764635-Agent-Status-and-Information) and look for `php_fpm` under the Checks section:

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)