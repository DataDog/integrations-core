# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.utils.headers import headers as agent_headers


DEFAULT_EXPECTED_CODE = r'(1|2|3)\d\d'


Config = namedtuple('Config',
                    'url, ntlm_domain, username, password, client_cert,'
                    'client_key, method, data, http_response_status_code,'
                    'timeout, include_content, headers, response_time,'
                    'content_match, reverse_content_match, tags,'
                    'disable_ssl_validation, ssl_expire, instance_ca_certs,'
                    'weakcipher, check_hostname, ignore_ssl_warning,'
                    'skip_proxy, allow_redirects, stream')


def from_instance(instance, default_ca_certs=None):
    """
    Create a config object from an instance dictionary
    """
    method = instance.get('method', 'get')
    data = instance.get('data', {})
    tags = instance.get('tags', [])
    ntlm_domain = instance.get('ntlm_domain')
    username = instance.get('username')
    password = instance.get('password')
    client_cert = instance.get('client_cert')
    client_key = instance.get('client_key')
    http_response_status_code = str(instance.get('http_response_status_code', DEFAULT_EXPECTED_CODE))
    timeout = int(instance.get('timeout', 10))
    config_headers = instance.get('headers', {})
    default_headers = is_affirmative(instance.get("include_default_headers", True))
    if default_headers:
        headers = agent_headers({})
    else:
        headers = {}
    headers.update(config_headers)
    url = instance.get('url')
    content_match = instance.get('content_match')
    reverse_content_match = is_affirmative(instance.get('reverse_content_match', False))
    response_time = is_affirmative(instance.get('collect_response_time', True))
    if not url:
        raise ConfigurationError("Bad configuration. You must specify a url")
    if not url.startswith("http"):
        raise ConfigurationError(b"The url {} must start with the scheme http or https".format(url))
    include_content = is_affirmative(instance.get('include_content', False))
    disable_ssl_validation = is_affirmative(instance.get('disable_ssl_validation', True))
    ssl_expire = is_affirmative(instance.get('check_certificate_expiration', True))
    instance_ca_certs = instance.get('ca_certs', default_ca_certs)
    weakcipher = is_affirmative(instance.get('weakciphers', False))
    ignore_ssl_warning = is_affirmative(instance.get('ignore_ssl_warning', False))
    check_hostname = is_affirmative(instance.get('check_hostname', True))
    skip_proxy = is_affirmative(
        instance.get('skip_proxy', instance.get('no_proxy', False)))
    allow_redirects = is_affirmative(instance.get('allow_redirects', True))
    stream = is_affirmative(instance.get('stream', False))

    return Config(url, ntlm_domain, username, password, client_cert, client_key,
                  method, data, http_response_status_code, timeout,
                  include_content, headers, response_time, content_match,
                  reverse_content_match, tags, disable_ssl_validation,
                  ssl_expire, instance_ca_certs, weakcipher, check_hostname,
                  ignore_ssl_warning, skip_proxy, allow_redirects, stream)
