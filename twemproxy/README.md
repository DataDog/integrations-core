# Overview

Get metrics from Twitter's twemproxy in real time to:

* Visualize client and server connectivity
* Correlate performance of the proxy to the Redis or Memcached server behind it

# Installation

Install the integration using `apt-get install dd-check-twemproxy`

# Configuration

Edit the `twemproxy.yaml` file to point to your server and port

# Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        twemproxy
        ---------
          - instance #0 [OK]
          - Collected 17 metrics, 0 events & 1 service check

