# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
try:
    import datadog_agent
except ImportError:
    datadog_agent = None


def headers(agentConfig, **kwargs):
    # Build the request headers
    version = __get_version(agentConfig)

    # ensure backward compatibility
    if 'http_method' not in kwargs:
        res = {
            'User-Agent': 'Datadog Agent/{}'.format(version),
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html, */*',
        }
    else:
        res = {
            'User-Agent': 'Datadog Agent/{}'.format(version),
            'Accept': 'text/html, */*',
        }

        if kwargs.get('http_method'):
            if kwargs.get('http_method').lower() in ('post', 'put', 'patch'):
                res['Content-Type'] = 'application/x-www-form-urlencoded'

    if 'http_host' in kwargs:
        res['Host'] = kwargs['http_host']
    return res


def __get_version(agentConfig):
    if datadog_agent:
        version = datadog_agent.get_version() or '0.0.0'
    else:
        version = agentConfig.get('version', '0.0.0')
    return version
