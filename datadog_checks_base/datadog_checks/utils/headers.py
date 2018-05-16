# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

def headers(agentConfig, **kwargs):
    # Build the request headers
    res = {
        'User-Agent': 'Datadog Agent/%s' % agentConfig.get('version', '0.0.0'),
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html, */*',
    }
    if 'http_host' in kwargs:
        res['Host'] = kwargs['http_host']
    return res
