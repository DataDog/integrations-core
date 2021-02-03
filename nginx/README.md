# Agent Check: Nginx

## Overview

The Datadog Agent can collect many metrics from NGINX instances, including (but not limited to)::

- Total requests
- Connections (e.g. accepted, handled, active)

For users of NGINX Plus, the commercial version of NGINX, the Agent can collect the significantly more metrics that NGINX Plus provides, like:

- Errors (e.g. 4xx codes, 5xx codes)
- Upstream servers (e.g. active connections, 5xx codes, health checks, etc.)
- Caches (e.g. size, hits, misses, etc.)
- SSL (e.g. handshakes, failed handshakes, etc.)


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For
containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these
instructions.

### Installation

The NGINX check pulls metrics from a local NGINX status endpoint, so your `nginx` binaries need to have been compiled with one of two NGINX status modules:

- [stub status module][2] - for open source NGINX
- [http status module][3] - only for NGINX Plus

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://nginx.org/en/docs/http/ngx_http_stub_status_module.html
[3]: https://nginx.org/en/docs/http/ngx_http_status_module.html