# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import quote_plus, urlencode, urlunparse


def _build_connection_string(self, hosts, scheme, username=None, password=None, database=None, options=None):
    # type: (list, str, str, str, str, dict) -> str
    """
    Build a server connection string from individual parts

    See https://docs.mongodb.com/manual/reference/connection-string/
    """

    def add_default_port(host):
        # type: (str) -> str
        if ':' not in host:
            return '{}:27017'.format(host)
        return host

    host = ','.join(add_default_port(host) for host in hosts)
    path = '/{}'.format(database) if database else '/'
    if username and password:
        netloc = '{}:{}@{}'.format(quote_plus(username), quote_plus(password), host)
    else:
        netloc = host

    path_params = ""
    query = urlencode(options or {})
    fragment = ""

    return urlunparse([scheme, netloc, path, path_params, query, fragment])


def build_url(scheme, host, path='/', username=None, password=None, query_params=None):
    # type: (str, str, str, str, str, dict) -> str
    """Build an URL from individual parts. Make sure that parts are properly URL-encoded."""

