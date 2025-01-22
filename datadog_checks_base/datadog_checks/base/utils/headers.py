# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.agent import datadog_agent


def _get_common_headers():
    return {  # Required by the HTTP spec. If missing, some websites may return junk (eg 404 responses).
        'Accept': '*/*',
        # Allow websites to send compressed responses.
        # (In theory, not including this header allows servers to send anything, but in practice servers are
        # typically conservative and send plain text, i.e. uncompressed responses.)
        'Accept-Encoding': 'gzip, deflate',
        # NOTE: we don't include a 'Connection' header. This is equivalent to using the spec-specific default
        # behavior, i.e. 'keep-alive' for HTTP/1.1, and 'close' for HTTP/1.0.
    }


def get_default_headers():
    # http://docs.python-requests.org/en/master/user/advanced/#header-ordering
    # Default to `0.0.0` if no version is found
    headers = {'User-Agent': 'Datadog Agent/{}'.format(datadog_agent.get_version() or '0.0.0')}
    headers.update(_get_common_headers())
    return headers


def update_headers(headers, extra_headers):
    # Ensure the values are strings
    headers.update((key, str(value)) for key, value in extra_headers.items())


def headers(agentConfig, **kwargs):
    # Build the request headers
    version = __get_version(agentConfig)
    res = {'User-Agent': 'Datadog Agent/{}'.format(version)}
    res.update(_get_common_headers())

    if 'http_host' in kwargs:
        res['Host'] = kwargs['http_host']
    return res


def __get_version(agentConfig):
    if datadog_agent:
        version = datadog_agent.get_version() or '0.0.0'
    else:
        version = agentConfig.get('version', '0.0.0')
    return version
