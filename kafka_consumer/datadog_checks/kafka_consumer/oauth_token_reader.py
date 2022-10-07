# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from requests import auth as requests_auth
from six import string_types

from datadog_checks.base.config import is_affirmative
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.time import get_timestamp


class AuthTokenOAuthReader(object):
    def __init__(self, config):
        self._url = config.get('url', '')
        if not isinstance(self._url, str):
            raise ConfigurationError('The `url` setting of `auth_token` reader must be a string')
        elif not self._url:
            raise ConfigurationError('The `url` setting of `auth_token` reader is required')

        self._client_id = config.get('client_id', '')
        if not isinstance(self._client_id, str):
            raise ConfigurationError('The `client_id` setting of `auth_token` reader must be a string')
        elif not self._client_id:
            raise ConfigurationError('The `client_id` setting of `auth_token` reader is required')

        self._client_secret = config.get('client_secret', '')
        if not isinstance(self._client_secret, str):
            raise ConfigurationError('The `client_secret` setting of `auth_token` reader must be a string')
        elif not self._client_secret:
            raise ConfigurationError('The `client_secret` setting of `auth_token` reader is required')

        self._basic_auth = config.get('basic_auth', False)
        if not isinstance(self._basic_auth, bool):
            raise ConfigurationError('The `basic_auth` setting of `auth_token` reader must be a boolean')

        self._fetch_options = {'token_url': self._url}
        if self._basic_auth:
            self._fetch_options['auth'] = requests_auth.HTTPBasicAuth(self._client_id, self._client_secret)
        else:
            self._fetch_options['client_id'] = self._client_id
            self._fetch_options['client_secret'] = self._client_secret

        if 'tls_ca_cert' in config:
            if isinstance(config['tls_ca_cert'], string_types):
                self._fetch_options['verify'] = config['tls_ca_cert']
            else:
                raise ConfigurationError('The `tls_ca_cert` setting of `auth_token` reader must be a string')
        else:
            self._fetch_options['verify'] = is_affirmative(config.get('tls_verify', True))

        if 'tls_cert' in config:
            if isinstance(config['tls_cert'], string_types):
                self._fetch_options['cert'] = config['tls_cert']
            else:
                raise ConfigurationError('The `tls_cert` setting of `auth_token` reader must be a string')

        self._token = None
        self._expiration = None

    def read(self, **request):
        if self._token is None or get_timestamp() >= self._expiration or 'error' in request:
            from oauthlib import oauth2
            import requests_oauthlib

            client = oauth2.BackendApplicationClient(client_id=self._client_id)
            oauth = requests_oauthlib.OAuth2Session(client=client)
            response = oauth.fetch_token(**self._fetch_options)

            # https://www.rfc-editor.org/rfc/rfc6749#section-5.2
            if 'error' in response:
                raise Exception('OAuth2 client credentials grant error: {}'.format(response['error']))

            # https://www.rfc-editor.org/rfc/rfc6749#section-4.4.3
            self._token = response['access_token']
            self._expiration = get_timestamp() + response['expires_in']

            return self._token
