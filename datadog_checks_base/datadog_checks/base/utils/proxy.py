# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import string_types
from six.moves.urllib.parse import urlparse


def config_proxy_skip(proxies, uri, skip_proxy=False):
    """
    Returns an amended copy of the proxies dictionary - used by `requests`,
    it will disable the proxy if the uri provided is to be reached directly.
    :param proxies A dict with existing proxies: `https`, `http`, and `no` are potential keys.
    :param uri URI to determine if a proxy is necessary or not.
    :param skip_proxy If `True`, the returned proxy dictionary will disable all proxies.
    """
    parsed_uri = urlparse(uri)

    # disable proxy if necessary
    if skip_proxy:
        proxies['http'] = ''
        proxies['https'] = ''
    elif proxies.get('no'):
        urls = []
        if isinstance(proxies['no'], string_types):
            urls = proxies['no'].replace(';', ',').split(",")
        elif isinstance(proxies['no'], list):
            urls = proxies['no']
        for url in urls:
            if url in parsed_uri.netloc:
                if 'http' in proxies:
                    proxies.pop('http')
                if 'https' in proxies:
                    proxies.pop('https')

    return proxies
