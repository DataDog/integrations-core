# Php_fpm Integration

## Overview

Enable the PHP-FPM check to monitor the state of your FPM pool and track requests performance.

## Installation

Install the `dd-check-php_fpm` package manually or with your favorite configuration manager.

## Configuration

1. Configure the Agent to connect to your FPM status endpoint (look at your pools definition).
Edit conf.yaml:
```
init_config:

instances:
  - # Get metrics from your FPM pool with this URL
    status_url: http://localhost/status
    # Get a reliable service check of you FPM pool with that one
    ping_url: http://localhost/ping
    # These 2 URLs should follow the options from your FPM pool
    # See http://php.net/manual/en/install.fpm.configuration.php
    #   * pm.status_path
    #   * ping.path
    # You should configure your fastcgi passthru (nginx/apache) to
    # catch these URLs and redirect them through the FPM pool target
    # you want to monitor (FPM `listen` directive in the config, usually
    # a UNIX socket or TCP socket.
    #
    # Use this if you have basic authentication on these pages
    # user: bits
    # password: D4T4D0G
    #
    # Array of custom tags
    # By default metrics and service check will be tagged by pool and host
    # tags:
    #   - instance:foo
```
2. Restart the Agent

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        php_fpm
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The php_fpm check is compatible with all major platforms
