# PHP-FPM Check

![PHP overview][1]

## Overview

The PHP-FPM check monitors the state of your FPM pool and tracks request performance.

## Setup

### Installation

The PHP-FPM check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers that use PHP-FPM.

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

#### Host

1. Edit the `php_fpm.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample php_fpm.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param status_url - string - required
     ## Get metrics from your FPM pool with this URL
     ## The status URLs should follow the options from your FPM pool
     ## See http://php.net/manual/en/install.fpm.configuration.php
     ##   * pm.status_path
     ## You should configure your fastcgi passthru (nginx/apache) to catch these URLs and
     ## redirect them through the FPM pool target you want to monitor (FPM `listen`
     ## directive in the config, usually a UNIX socket or TCP socket.
     #
     - status_url: http://localhost/status

       ## @param ping_url - string - required
       ## Get a reliable service check of your FPM pool with `ping_url` parameter
       ## The ping URLs should follow the options from your FPM pool
       ## See http://php.net/manual/en/install.fpm.configuration.php
       ##   * ping.path
       ## You should configure your fastcgi passthru (nginx/apache) to
       ## catch these URLs and redirect them through the FPM pool target
       ## you want to monitor (FPM `listen` directive in the config, usually
       ## a UNIX socket or TCP socket.
       #
       ping_url: http://localhost/ping

       ## @param use_fastcgi - boolean - required - default: false
       ## Communicate directly with PHP-FPM using FastCGI
       #
       use_fastcgi: false

       ## @param ping_reply - string - required
       ## Set the expected reply to the ping.
       #
       ping_reply: pong
   ```

2. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `php_fpm`                                                                                                                |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                                            |
| `<INSTANCE_CONFIG>`  | `{"status_url":"http://%%host%%/status", "ping_url":"http://%%host%%/ping", "use_fastcgi": false, "ping_reply": "pong"}` |

#### Extras

##### Multiple pools

It is possible to monitor multiple PHP-FPM pools using the same proxy server, a common scenario when running on Kubernetes. To do so, modify your server's routes to point to different PHP-FPM instances. Here is an example NGINX configuration:

```text
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

##### Unix sockets

If your PHP-FPM installation uses unix sockets, you have to use the below syntax for `status_url`, `ping_url` and enable `use_fastcgi`:

| Parameter     | Value                             |
| ------------- | --------------------------------- |
| `status_url`  | `unix:///<FILE_PATH>.sock/status` |
| `ping_url`    | `unix:///<FILE_PATH>.sock/ping`   |
| `ping_reply`  | `pong`                            |
| `use_fastcgi` | `true`                            |

**Note**: With Autodiscovery, if the Agent runs in a separate container/task/pod, it doesn't have access to the Unix sockets file of your FPM pool. It order to address this, run the Agent as a sidecar.

### Validation

[Run the Agent's `status` subcommand][7] and look for `php_fpm` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

The PHP-FPM check does not include any events.

### Service Checks

`php_fpm.can_ping`:

Returns CRITICAL if the Agent cannot ping PHP-FPM at the configured `ping_url`, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/php_fpm/images/phpfpmoverview.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/php_fpm/datadog_checks/php_fpm/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/autodiscovery/integrations/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/php_fpm/metadata.csv
[9]: https://docs.datadoghq.com/help
