# PHP-FPM Check

![PHP overview][8]

## Overview

The PHP-FPM check monitors the state of your FPM pool and tracks request performance.

## Setup
### Installation

The PHP-FPM check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers that use PHP-FPM.

### Configuration

Edit the `php_fpm.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9]. See the [sample php_fpm.d/conf.yaml][2] for all available configuration options:

```
init_config:

instances:
  - status_url: http://localhost/status # or whatever pm.status_path is set to in your PHP INI
    ping_url: http://localhost/ping     # or whatever ping.path is set to in your PHP INI
    ping_reply: pong                    # the reply to expect from ping; default is 'pong'
 #  user: <YOUR_USERNAME>     # if the status and ping URLs require HTTP basic auth
 #  password: <YOUR_PASSWORD> # if the status and ping URLs require HTTP basic auth
 #  http_host: <HOST>         # if your FPM pool is only accessible via a specific HTTP vhost
 #  tags:
 #    - instance:foo
```

Configuration Options:

* `status_url` (Required) - URL for the PHP FPM status page defined in the fpm pool config file (pm.status_path)
* `ping_url` (Required) - URL for the PHP FPM ping page defined in the fpm pool config file (ping.path)
* `use_fastcgi` (Optional) - Communicate directly with PHP-FPM using FastCGI
* `ping_reply` (Required) - Reply from the ping_url. Unless you define a reply, it is `pong`
* `user` (Optional) - Used if you have set basic authentication on the status and ping pages
* `password` (Optional) - Used if you have set basic authentication on the status and ping pages
* `http_host` (Optional) - If your FPM pool is only accessible via a specific HTTP vhost, specify it here

[Restart the Agent][3] to start sending PHP-FPM metrics to Datadog.

#### Multiple pools

It is also possible to monitor multiple PHP-FPM pools using the same proxy server, a common scenario when running on Kubernetes.

To do so, you can modify your server's routes to point to different PHP-FPM instances. Here is an example Nginx configuration:

```
server {
    ...

    location ~ ^/(status1|ping1)$ {
        access_log off;
        fastcgi_pass instance1_ip:instance1_port;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    location ~ ^/(status2|ping2)$ {
        access_log off;
        fastcgi_pass instance2_ip:instance2_port;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
}
```

If you find this approach too tedious at scale, setting `use_fastcgi` to `true` instructs the check to bypass any proxy servers and communicate directly with PHP-FPM using FastCGI. The default port is `9000` for when omitted from `status_url` or `ping_url`.

### Validation

[Run the Agent's `status` subcommand][4] and look for `php_fpm` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The PHP-FPM check does not include any events at this time.

### Service Checks

`php_fpm.can_ping`:

Returns CRITICAL if the Agent cannot ping PHP-FPM at the configured `ping_url`, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/php_fpm/datadog_checks/php_fpm/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/php_fpm/metadata.csv
[6]: https://docs.datadoghq.com/help/
[8]: https://raw.githubusercontent.com/DataDog/integrations-core/master/php_fpm/images/phpfpmoverview.png
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
