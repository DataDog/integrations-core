# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict

from six import iteritems

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


def get_default_headers():
    # http://docs.python-requests.org/en/master/user/advanced/#header-ordering
    # TODO: Use built-in when we drop Python 2 as dictionaries are guaranteed to be ordered in Python 3.6+ (and PyPy)
    return OrderedDict(
        (
            # Default to `0.0.0` if no version is found
            ('User-Agent', 'Datadog Agent/{}'.format(datadog_agent.get_version() or '0.0.0')),
        )
    )


def update_headers(headers, extra_headers):
    # Ensure the values are strings
    headers.update((key, str(value)) for key, value in iteritems(extra_headers))


def headers(agentConfig, **kwargs):
    # Build the request headers
    version = __get_version(agentConfig)
    res = {'User-Agent': 'Datadog Agent/{}'.format(version)}

    if 'http_host' in kwargs:
        res['Host'] = kwargs['http_host']
    return res


def __get_version(agentConfig):
    if datadog_agent:
        version = datadog_agent.get_version() or '0.0.0'
    else:
        version = agentConfig.get('version', '0.0.0')
    return version
