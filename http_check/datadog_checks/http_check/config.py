# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple

from datadog_checks.base import ConfigurationError, ensure_unicode, is_affirmative
from datadog_checks.base.utils.headers import headers as agent_headers

DEFAULT_EXPECTED_CODE = r'(1|2|3)\d\d'


class CaseInsensitiveDict(dict):
    """Dict that merges header names case-insensitively, keeping the most recently set casing."""

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.update(data)

    def __setitem__(self, key, value):
        existing_key = self.matching_key(key)
        if existing_key is not None and existing_key != key:
            super().__delitem__(existing_key)
        super().__setitem__(key, value)

    def __getitem__(self, key):
        existing_key = self.matching_key(key)
        if existing_key is None:
            raise KeyError(key)
        return super().__getitem__(existing_key)

    def __delitem__(self, key):
        existing_key = self.matching_key(key)
        if existing_key is None:
            raise KeyError(key)
        super().__delitem__(existing_key)

    def __contains__(self, key):
        return self.matching_key(key) is not None

    def get(self, key, default=None):
        existing_key = self.matching_key(key)
        return super().get(existing_key, default) if existing_key is not None else default

    def pop(self, key, *args):
        existing_key = self.matching_key(key)
        if existing_key is None:
            if args:
                return args[0]
            raise KeyError(key)
        return super().pop(existing_key)

    def setdefault(self, key, default=None):
        existing_key = self.matching_key(key)
        if existing_key is not None:
            return super().__getitem__(existing_key)
        self[key] = default
        return default

    def copy(self):
        return CaseInsensitiveDict(self)

    def update(self, data=(), **kwargs):
        for key, value in dict(data, **kwargs).items():
            self[key] = value

    def matching_key(self, key):
        lowered = key.lower()
        for existing in self:
            if existing.lower() == lowered:
                return existing
        return None

    def __eq__(self, other):
        if isinstance(other, dict):
            return {key.lower(): value for key, value in self.items()} == {
                key.lower(): value for key, value in other.items()
            }
        return NotImplemented


Config = namedtuple(
    'Config',
    [
        'url',
        'client_cert',
        'client_key',
        'method',
        'data',
        'http_response_status_code',
        'include_content',
        'headers',
        'response_time',
        'content_match',
        'reverse_content_match',
        'tags',
        'ssl_expire',
        'instance_ca_certs',
        'check_hostname',
        'stream',
        'use_cert_from_response',
    ],
)


def from_instance(instance, default_ca_certs=None):
    """
    Create a config object from an instance dictionary
    """
    method = instance.get('method', 'get')
    data = instance.get('data', {})
    tags = instance.get('tags', [])
    client_cert = instance.get('tls_cert') or instance.get('client_cert')
    client_key = instance.get('tls_private_key') or instance.get('client_key')
    http_response_status_code = str(instance.get('http_response_status_code', DEFAULT_EXPECTED_CODE))
    config_headers = instance.get('headers', {})
    default_headers = is_affirmative(instance.get("include_default_headers", True))
    if default_headers:
        headers = CaseInsensitiveDict(agent_headers({}))
    else:
        headers = CaseInsensitiveDict({})
    headers.update(config_headers)
    url = instance.get('url')
    if url is not None:
        url = ensure_unicode(url)
    content_match = instance.get('content_match')
    if content_match is not None:
        content_match = ensure_unicode(content_match)
    reverse_content_match = is_affirmative(instance.get('reverse_content_match', False))
    response_time = is_affirmative(instance.get('collect_response_time', True))
    if not url:
        raise ConfigurationError("Bad configuration. You must specify a url")
    if not url.startswith("http"):
        raise ConfigurationError("The url {} must start with the scheme http or https".format(url))
    include_content = is_affirmative(instance.get('include_content', False))
    ssl_expire = is_affirmative(instance.get('check_certificate_expiration', True))
    instance_ca_certs = instance.get('tls_ca_cert', instance.get('ca_certs', default_ca_certs))
    check_hostname = is_affirmative(instance.get('check_hostname', True))
    stream = is_affirmative(instance.get('stream', False))
    use_cert_from_response = is_affirmative(instance.get('use_cert_from_response', False))
    if use_cert_from_response:
        stream = True

    return Config(
        url,
        client_cert,
        client_key,
        method,
        data,
        http_response_status_code,
        include_content,
        headers,
        response_time,
        content_match,
        reverse_content_match,
        tags,
        ssl_expire,
        instance_ca_certs,
        check_hostname,
        stream,
        use_cert_from_response,
    )
