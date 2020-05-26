# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import quote_plus, urlencode, urlunparse


def build_url(scheme, host, path='/', username=None, password=None, query_params=None):
    # type: (str, str, str, str, str, dict) -> str
    """Build an URL from individual parts. Make sure that parts are properly URL-encoded."""
    if username and password:
        netloc = '{}:{}@{}'.format(quote_plus(username), quote_plus(password), host)
    else:
        netloc = host

    path_params = ""
    query = urlencode(query_params or {})
    fragment = ""

    return urlunparse([scheme, netloc, path, path_params, query, fragment])
