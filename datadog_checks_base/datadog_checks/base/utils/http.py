# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
from contextlib import contextmanager
from ipaddress import ip_address, ip_network

import requests
from requests import auth as requests_auth
from requests_toolbelt.adapters import host_header_ssl
from six import PY2, iteritems, string_types
from six.moves.urllib.parse import urlparse
from urllib3.exceptions import InsecureRequestWarning

from ..config import is_affirmative
from ..errors import ConfigurationError
from .common import ensure_unicode
from .headers import get_default_headers, update_headers
from .warnings_util import disable_warnings_ctx

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

# Import lazily to reduce memory footprint and ease installation for development
requests_aws = None
requests_kerberos = None
requests_ntlm = None

LOGGER = logging.getLogger(__file__)

# The timeout should be slightly larger than a multiple of 3,
# which is the default TCP packet retransmission window. See:
# https://tools.ietf.org/html/rfc2988
DEFAULT_TIMEOUT = 10

STANDARD_FIELDS = {
    'auth_type': 'basic',
    'aws_host': None,
    'aws_region': None,
    'aws_service': None,
    'connect_timeout': None,
    'extra_headers': None,
    'headers': None,
    'kerberos_auth': None,
    'kerberos_cache': None,
    'kerberos_delegate': False,
    'kerberos_force_initiate': False,
    'kerberos_hostname': None,
    'kerberos_keytab': None,
    'kerberos_principal': None,
    'log_requests': False,
    'ntlm_domain': None,
    'password': None,
    'persist_connections': False,
    'proxy': None,
    'read_timeout': None,
    'skip_proxy': False,
    'tls_ca_cert': None,
    'tls_cert': None,
    'tls_use_host_header': False,
    'tls_ignore_warning': False,
    'tls_private_key': None,
    'tls_verify': True,
    'timeout': DEFAULT_TIMEOUT,
    'username': None,
}
# For any known legacy fields that may be widespread
DEFAULT_REMAPPED_FIELDS = {
    'kerberos': {'name': 'kerberos_auth'},
    # TODO: Remove in 6.13
    'no_proxy': {'name': 'skip_proxy'},
}
PROXY_SETTINGS_DISABLED = {
    # This will instruct `requests` to ignore the `HTTP_PROXY`/`HTTPS_PROXY`
    # environment variables. If the proxy options `http`/`https` are missing
    # or are `None` then `requests` will use the aforementioned environment
    # variables, hence the need to set each to an empty string.
    'http': '',
    'https': '',
}

KERBEROS_STRATEGIES = {}


class RequestsWrapper(object):
    __slots__ = (
        '_session',
        'tls_use_host_header',
        'ignore_tls_warning',
        'log_requests',
        'logger',
        'no_proxy_uris',
        'options',
        'persist_connections',
        'request_hooks',
    )

    def __init__(self, instance, init_config, remapper=None, logger=None):
        self.logger = logger or LOGGER
        default_fields = dict(STANDARD_FIELDS)

        # Update the default behavior for global settings
        default_fields['log_requests'] = init_config.get('log_requests', default_fields['log_requests'])
        default_fields['skip_proxy'] = init_config.get('skip_proxy', default_fields['skip_proxy'])
        default_fields['timeout'] = init_config.get('timeout', default_fields['timeout'])
        default_fields['tls_ignore_warning'] = init_config.get(
            'tls_ignore_warning', default_fields['tls_ignore_warning']
        )

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

            # Invert default booleans if need be
            default = default_fields[field]
            if data.get('invert'):
                default = not default

            # Get value, with a possible default
            value = instance.get(remapped_field, data.get('default', default))

            # Invert booleans if need be
            if data.get('invert'):
                value = not is_affirmative(value)

            config[field] = value

        # http://docs.python-requests.org/en/master/user/advanced/#timeouts
        connect_timeout = read_timeout = float(config['timeout'])
        if config['connect_timeout'] is not None:
            connect_timeout = float(config['connect_timeout'])

        if config['read_timeout'] is not None:
            read_timeout = float(config['read_timeout'])

        # http://docs.python-requests.org/en/master/user/quickstart/#custom-headers
        # http://docs.python-requests.org/en/master/user/advanced/#header-ordering
        headers = get_default_headers()
        if config['headers']:
            headers.clear()
            update_headers(headers, config['headers'])

        if config['extra_headers']:
            update_headers(headers, config['extra_headers'])

        # https://toolbelt.readthedocs.io/en/latest/adapters.html#hostheaderssladapter
        self.tls_use_host_header = is_affirmative(config['tls_use_host_header']) and 'Host' in headers

        # http://docs.python-requests.org/en/master/user/authentication/
        auth_type = config['auth_type'].lower()
        if auth_type not in AUTH_TYPES:
            self.logger.warning('auth_type %s is not supported, defaulting to basic', auth_type)
            auth_type = 'basic'

        if auth_type == 'basic':
            if config['kerberos_auth']:
                self.logger.warning(
                    'The ability to use Kerberos auth without explicitly setting auth_type to '
                    '`kerberos` is deprecated and will be removed in Agent 8'
                )
                auth_type = 'kerberos'
            elif config['ntlm_domain']:
                self.logger.warning(
                    'The ability to use NTLM auth without explicitly setting auth_type to '
                    '`ntlm` is deprecated and will be removed in Agent 8'
                )
                auth_type = 'ntlm'

        auth = AUTH_TYPES[auth_type](config)

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
            'timeout': (connect_timeout, read_timeout),
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
        self.persist_connections = self.tls_use_host_header or is_affirmative(config['persist_connections'])
        self._session = None

        # Whether or not to log request information like method and url
        self.log_requests = is_affirmative(config['log_requests'])

        # Context managers that should wrap all requests
        self.request_hooks = []
        if self.ignore_tls_warning:
            self.request_hooks.append(self.handle_tls_warning)

        if config['kerberos_keytab']:
            self.request_hooks.append(lambda: handle_kerberos_keytab(config['kerberos_keytab']))
        if config['kerberos_cache']:
            self.request_hooks.append(lambda: handle_kerberos_cache(config['kerberos_cache']))

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
            self.logger.debug(u'Sending %s request to %s', method.upper(), url)

        if self.no_proxy_uris and should_bypass_proxy(url, self.no_proxy_uris):
            options.setdefault('proxies', PROXY_SETTINGS_DISABLED)

        persist = options.pop('persist', None)
        if persist is None:
            persist = self.persist_connections

        new_options = self.populate_options(options)

        extra_headers = options.pop('extra_headers', None)
        if extra_headers is not None:
            new_options['headers'] = new_options['headers'].copy()
            new_options['headers'].update(extra_headers)

        with ExitStack() as stack:
            for hook in self.request_hooks:
                stack.enter_context(hook())

            if persist:
                return getattr(self.session, method)(url, **new_options)
            else:
                return getattr(requests, method)(url, **new_options)

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
        with disable_warnings_ctx(InsecureRequestWarning, disable=True):
            yield

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()

            # Enables HostHeaderSSLAdapter
            # https://toolbelt.readthedocs.io/en/latest/adapters.html#hostheaderssladapter
            if self.tls_use_host_header:
                self._session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())

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


@contextmanager
def handle_kerberos_keytab(keytab_file):
    # There are no keytab options in any wrapper libs. The env var will be
    # used directly by C lib, see: https://web.mit.edu/kerberos/krb5-1.11
    #
    # `Add support for a "default client keytab". Its location is determined by
    # the KRB5_CLIENT_KTNAME environment variable, the default_client_keytab
    # profile relation, or a hardcoded path (TBD).`
    old_keytab_path = os.environ.get('KRB5_CLIENT_KTNAME')
    os.environ['KRB5_CLIENT_KTNAME'] = keytab_file

    yield

    if old_keytab_path is None:
        del os.environ['KRB5_CLIENT_KTNAME']
    else:
        os.environ['KRB5_CLIENT_KTNAME'] = old_keytab_path


@contextmanager
def handle_kerberos_cache(cache_file_path):
    """
    :param cache_file_path: Location of the Kerberos credentials (ticket) cache. It defaults to /tmp/krb5cc_[uid]
    """
    old_cache_path = os.environ.get('KRB5CCNAME')
    os.environ['KRB5CCNAME'] = cache_file_path

    yield

    if old_cache_path is None:
        del os.environ['KRB5CCNAME']
    else:
        os.environ['KRB5CCNAME'] = old_cache_path


def should_bypass_proxy(url, no_proxy_uris):
    # Accepts a URL and a list of no_proxy URIs
    # Returns True if URL should bypass the proxy.
    parsed_uri = urlparse(url).hostname

    for no_proxy_uri in no_proxy_uris:
        try:
            # If no_proxy_uri is an IP or IP CIDR.
            # A ValueError is raised if address does not represent a valid IPv4 or IPv6 address.
            ipnetwork = ip_network(ensure_unicode(no_proxy_uri))
            ipaddress = ip_address(ensure_unicode(parsed_uri))
            if ipaddress in ipnetwork:
                return True
        except ValueError:
            # Treat no_proxy_uri as a domain name
            # A domain name matches that name and all subdomains.
            #   e.g. "foo.com" matches "foo.com" and "bar.foo.com"
            # A domain name with a leading "." matches subdomains only.
            #   e.g. ".y.com" matches "x.y.com" but not "y.com".
            dot_no_proxy_uri = no_proxy_uri if no_proxy_uri.startswith(".") else ".{}".format(no_proxy_uri)
            if no_proxy_uri == parsed_uri or parsed_uri.endswith(dot_no_proxy_uri):
                return True
    return False


def create_basic_auth(config):
    # Since this is the default case, only activate when all fields are explicitly set
    if config['username'] and config['password']:
        return (config['username'], config['password'])


def create_digest_auth(config):
    return requests_auth.HTTPDigestAuth(config['username'], config['password'])


def create_ntlm_auth(config):
    global requests_ntlm
    if requests_ntlm is None:
        import requests_ntlm

    return requests_ntlm.HttpNtlmAuth(config['ntlm_domain'], config['password'])


def create_kerberos_auth(config):
    global requests_kerberos
    if requests_kerberos is None:
        import requests_kerberos

        KERBEROS_STRATEGIES['required'] = requests_kerberos.REQUIRED
        KERBEROS_STRATEGIES['optional'] = requests_kerberos.OPTIONAL
        KERBEROS_STRATEGIES['disabled'] = requests_kerberos.DISABLED

    # For convenience
    if config['kerberos_auth'] is None or is_affirmative(config['kerberos_auth']):
        config['kerberos_auth'] = 'required'

    if config['kerberos_auth'] not in KERBEROS_STRATEGIES:
        raise ConfigurationError(
            'Invalid Kerberos strategy `{}`, must be one of: {}'.format(
                config['kerberos_auth'], ' | '.join(KERBEROS_STRATEGIES)
            )
        )

    return requests_kerberos.HTTPKerberosAuth(
        mutual_authentication=KERBEROS_STRATEGIES[config['kerberos_auth']],
        delegate=is_affirmative(config['kerberos_delegate']),
        force_preemptive=is_affirmative(config['kerberos_force_initiate']),
        hostname_override=config['kerberos_hostname'],
        principal=config['kerberos_principal'],
    )


def create_aws_auth(config):
    global requests_aws
    if requests_aws is None:
        from aws_requests_auth import boto_utils as requests_aws

    for setting in ('aws_host', 'aws_region', 'aws_service'):
        if not config[setting]:
            raise ConfigurationError('AWS auth requires the setting `{}`'.format(setting))

    return requests_aws.BotoAWSRequestsAuth(
        aws_host=config['aws_host'], aws_region=config['aws_region'], aws_service=config['aws_service']
    )


AUTH_TYPES = {
    'basic': create_basic_auth,
    'digest': create_digest_auth,
    'ntlm': create_ntlm_auth,
    'kerberos': create_kerberos_auth,
    'aws': create_aws_auth,
}


# For documentation generation
# TODO: use an enum and remove STANDARD_FIELDS when mkdocstrings supports it
class StandardFields(object):
    pass


if not PY2:
    StandardFields.__doc__ = '\n'.join('- `{}`'.format(field) for field in STANDARD_FIELDS)
