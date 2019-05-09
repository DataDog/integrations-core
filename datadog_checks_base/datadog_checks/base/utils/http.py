# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
import warnings
from collections import OrderedDict
from contextlib import contextmanager

import requests
from six import iteritems, string_types
from six.moves.urllib.parse import urlparse
from urllib3.exceptions import InsecureRequestWarning

from ..config import is_affirmative

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

LOGGER = logging.getLogger(__file__)

STANDARD_FIELDS = {
    'headers': None,
    'log_requests': False,
    'password': None,
    'persist_connections': False,
    'proxy': None,
    'skip_proxy': False,
    'tls_ca_cert': None,
    'tls_cert': None,
    'tls_ignore_warning': False,
    'tls_private_key': None,
    'tls_verify': True,
    'timeout': 10,
    'username': None,
}
# For any known legacy fields that may be widespread
DEFAULT_REMAPPED_FIELDS = {
    # TODO: Remove in 6.13
    'no_proxy': {'name': 'skip_proxy'}
}
PROXY_SETTINGS_DISABLED = {
    # This will instruct `requests` to ignore the `HTTP_PROXY`/`HTTPS_PROXY`
    # environment variables. If the proxy options `http`/`https` are missing
    # or are `None` then `requests` will use the aforementioned environment
    # variables, hence the need to set each to an empty string.
    'http': '',
    'https': '',
}


class RequestsWrapper(object):
    __slots__ = (
        '_session',
        'ignore_tls_warning',
        'log_requests',
        'logger',
        'no_proxy_uris',
        'options',
        'persist_connections',
    )

    # For modifying the warnings filter since the context
    # manager that is provided changes module constants
    warning_lock = threading.Lock()

    def __init__(self, instance, init_config, remapper=None, logger=None):
        self.logger = logger or LOGGER
        default_fields = dict(STANDARD_FIELDS)

        # Update the default behavior for global settings
        default_fields['log_requests'] = init_config.get('log_requests', default_fields['log_requests'])
        default_fields['skip_proxy'] = init_config.get('skip_proxy', default_fields['skip_proxy'])

        # Populate with the default values
        config = {field: instance.get(field, value) for field, value in iteritems(default_fields)}

        # Support non-standard (usually legacy) configurations, for example:
        # {
        #     'disable_ssl_validation': {
        #         'name': 'tls_verify',
        #         'default': False,
        #         'invert': True,
        #     },
        #     ...
        # }
        if remapper is None:
            remapper = {}

        remapper.update(DEFAULT_REMAPPED_FIELDS)

        for remapped_field, data in iteritems(remapper):
            field = data.get('name')

            # Ignore fields we don't recognize
            if field not in STANDARD_FIELDS:
                continue

            # Ignore remapped fields if the standard one is already used
            if field in instance:
                continue

            # Get value, with a possible default
            value = instance.get(remapped_field, data.get('default', default_fields[field]))

            # Invert booleans if need be
            if data.get('invert'):
                value = not is_affirmative(value)

            config[field] = value

        # http://docs.python-requests.org/en/master/user/advanced/#timeouts
        timeout = float(config['timeout'])

        # http://docs.python-requests.org/en/master/user/quickstart/#custom-headers
        # http://docs.python-requests.org/en/master/user/advanced/#header-ordering
        headers = None
        if config['headers']:
            headers = OrderedDict((key, str(value)) for key, value in iteritems(config['headers']))

        # http://docs.python-requests.org/en/master/user/authentication/
        auth = None
        if config['username'] and config['password']:
            auth = (config['username'], config['password'])

        # http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification
        verify = True
        if isinstance(config['tls_ca_cert'], string_types):
            verify = config['tls_ca_cert']
        elif not is_affirmative(config['tls_verify']):
            verify = False

        # http://docs.python-requests.org/en/master/user/advanced/#client-side-certificates
        cert = None
        if isinstance(config['tls_cert'], string_types):
            if isinstance(config['tls_private_key'], string_types):
                cert = (config['tls_cert'], config['tls_private_key'])
            else:
                cert = config['tls_cert']

        # http://docs.python-requests.org/en/master/user/advanced/#proxies
        no_proxy_uris = None
        if is_affirmative(config['skip_proxy']):
            proxies = PROXY_SETTINGS_DISABLED.copy()
        else:
            # Order of precedence is:
            # 1. instance
            # 2. init_config
            # 3. agent config
            proxies = config['proxy'] or init_config.get('proxy')

            # TODO: Deprecate this flag now that we support skip_proxy in init_config
            if not proxies and is_affirmative(init_config.get('use_agent_proxy', True)):
                proxies = datadog_agent.get_config('proxy')

            if proxies:
                proxies = proxies.copy()

                # TODO: Pass `no_proxy` directly to `requests` once this issue is fixed:
                # https://github.com/kennethreitz/requests/issues/5000
                if 'no_proxy' in proxies:
                    no_proxy_uris = proxies.pop('no_proxy')

                    if isinstance(no_proxy_uris, string_types):
                        no_proxy_uris = no_proxy_uris.replace(';', ',').split(',')
            else:
                proxies = None

        # Default options
        self.options = {
            'auth': auth,
            'cert': cert,
            'headers': headers,
            'proxies': proxies,
            'timeout': timeout,
            'verify': verify,
        }

        # For manual parsing until `requests` properly handles `no_proxy`
        self.no_proxy_uris = no_proxy_uris

        # Ignore warnings for lack of SSL validation
        self.ignore_tls_warning = is_affirmative(config['tls_ignore_warning'])

        # For connection and cookie persistence, if desired. See:
        # https://en.wikipedia.org/wiki/HTTP_persistent_connection#Advantages
        # http://docs.python-requests.org/en/master/user/advanced/#session-objects
        # http://docs.python-requests.org/en/master/user/advanced/#keep-alive
        self.persist_connections = is_affirmative(config['persist_connections'])
        self._session = None

        self.log_requests = is_affirmative(config['log_requests'])

    def get(self, url, **options):
        return self._request('get', url, options)

    def post(self, url, **options):
        return self._request('post', url, options)

    def head(self, url, **options):
        return self._request('head', url, options)

    def put(self, url, **options):
        return self._request('put', url, options)

    def patch(self, url, **options):
        return self._request('patch', url, options)

    def delete(self, url, **options):
        return self._request('delete', url, options)

    def _request(self, method, url, options):
        if self.log_requests:
            self.logger.debug(u'Sending {} request to {}'.format(method.upper(), url))

        if self.no_proxy_uris:
            parsed_uri = urlparse(url)

            for no_proxy_uri in self.no_proxy_uris:
                if no_proxy_uri in parsed_uri.netloc:
                    options.setdefault('proxies', PROXY_SETTINGS_DISABLED)
                    break

        persist = options.pop('persist', None)
        if persist is None:
            persist = self.persist_connections

        with self.handle_tls_warning():
            if persist:
                return getattr(self.session, method)(url, **options)
            else:
                return getattr(requests, method)(url, **self.populate_options(options))

    def populate_options(self, options):
        # Avoid needless dictionary update if there are no options
        if not options:
            return self.options

        for option, value in iteritems(self.options):
            # Make explicitly set options take precedence
            options.setdefault(option, value)

        return options

    @contextmanager
    def handle_tls_warning(self):
        with self.warning_lock:

            with warnings.catch_warnings():
                if self.ignore_tls_warning:
                    warnings.simplefilter('ignore', InsecureRequestWarning)

                yield

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()

            # Attributes can't be passed to the constructor
            for option, value in iteritems(self.options):
                setattr(self._session, option, value)

        return self._session

    def __del__(self):  # no cov
        try:
            self._session.close()
        except AttributeError:
            # A persistent connection was never used or an error occurred during instantiation
            # before _session was ever defined (since __del__ executes even if __init__ fails).
            pass
