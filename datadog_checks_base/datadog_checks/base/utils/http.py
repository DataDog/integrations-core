# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import re
import ssl
from contextlib import contextmanager
from copy import deepcopy
from io import open
from ipaddress import ip_address, ip_network

import requests
import requests_unixsocket
from cryptography.x509 import load_der_x509_certificate
from cryptography.x509.extensions import ExtensionNotFound
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID
from requests import auth as requests_auth
from requests.exceptions import SSLError
from requests_toolbelt.adapters import host_header_ssl
from six import PY2, iteritems, string_types
from six.moves.urllib.parse import quote, urlparse, urlunparse

from ..config import is_affirmative
from ..errors import ConfigurationError
from .common import ensure_bytes, ensure_unicode
from .headers import get_default_headers, update_headers
from .network import CertAdapter, closing, create_socket_connection
from .time import get_timestamp

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
jwt = None
default_backend = None
serialization = None

LOGGER = logging.getLogger(__file__)

# The timeout should be slightly larger than a multiple of 3,
# which is the default TCP packet retransmission window. See:
# https://tools.ietf.org/html/rfc2988
DEFAULT_TIMEOUT = 10

STANDARD_FIELDS = {
    'auth_token': None,
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
    'use_legacy_auth_encoding': True,
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

UDS_SCHEME = 'unix'


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
        'auth_token_handler',
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

        # Set up any auth token handlers
        if config['auth_token'] is not None:
            self.auth_token_handler = create_auth_token_handler(config['auth_token'])
        else:
            self.auth_token_handler = None

        # Context managers that should wrap all requests
        self.request_hooks = []

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

    def options_method(self, url, **options):
        return self._request('options', url, options)

    def _request(self, method, url, options):
        if self.log_requests:
            self.logger.debug(u'Sending %s request to %s', method.upper(), url)

        if self.no_proxy_uris and should_bypass_proxy(url, self.no_proxy_uris):
            options.setdefault('proxies', PROXY_SETTINGS_DISABLED)

        persist = options.pop('persist', None)
        if persist is None:
            persist = self.persist_connections

        new_options = self.populate_options(options)

        if url.startswith('https') and not self.ignore_tls_warning and not new_options['verify']:
            self.logger.warning(u'An unverified HTTPS request is being made to %s', url)

        extra_headers = options.pop('extra_headers', None)
        if extra_headers is not None:
            new_options['headers'] = new_options['headers'].copy()
            new_options['headers'].update(extra_headers)

        if is_uds_url(url):
            persist = True  # UDS support is only enabled on the shared session.
            url = quote_uds_url(url)

        self.handle_auth_token(method=method, url=url, default_options=self.options)

        with ExitStack() as stack:
            for hook in self.request_hooks:
                stack.enter_context(hook())
            if persist:
                request_method = getattr(self.session, method)
            else:
                request_method = getattr(requests, method)

            if self.auth_token_handler:
                try:
                    response = self.make_request_aia_chasing(request_method, method, url, new_options, persist)
                    response.raise_for_status()
                except Exception as e:
                    self.logger.debug(u'Renewing auth token, as an error occurred: %s', e)
                    self.handle_auth_token(method=method, url=url, default_options=self.options, error=str(e))
                    response = self.make_request_aia_chasing(request_method, method, url, new_options, persist)
            else:
                response = self.make_request_aia_chasing(request_method, method, url, new_options, persist)
            return response

    def make_request_aia_chasing(self, request_method, method, url, new_options, persist):
        try:
            response = request_method(url, **new_options)
        except SSLError as e:
            # fetch the intermediate certs
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname
            certs = self.fetch_intermediate_certs(hostname)
            if not certs:
                raise e
            # retry the connection via session object
            certadapter = CertAdapter(certs=certs)
            if not persist:
                session = requests.Session()
                for option, value in iteritems(self.options):
                    setattr(session, option, value)
            else:
                session = self.session
            request_method = getattr(session, method)
            session.mount(url, certadapter)
            response = request_method(url, **new_options)
        return response

    def populate_options(self, options):
        # Avoid needless dictionary update if there are no options
        if not options:
            return self.options

        for option, value in iteritems(self.options):
            # Make explicitly set options take precedence
            options.setdefault(option, value)

        return options

    def fetch_intermediate_certs(self, hostname):
        # TODO: prefer stdlib implementation when available, see https://bugs.python.org/issue18617
        certs = []

        try:
            sock = create_socket_connection(hostname)
        except Exception as e:
            self.logger.error('Error occurred while connecting to socket to discover intermediate certificates: %s', e)
            return certs

        with closing(sock):
            try:
                context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
                context.verify_mode = ssl.CERT_NONE

                with closing(context.wrap_socket(sock, server_hostname=hostname)) as secure_sock:
                    der_cert = secure_sock.getpeercert(binary_form=True)
            except Exception as e:
                self.logger.error('Error occurred while getting cert to discover intermediate certificates:', e)
                return certs

        self.load_intermediate_certs(der_cert, certs)
        return certs

    def load_intermediate_certs(self, der_cert, certs):
        # https://tools.ietf.org/html/rfc3280#section-4.2.2.1
        # https://tools.ietf.org/html/rfc5280#section-5.2.7
        try:
            cert = load_der_x509_certificate(der_cert)
        except Exception as e:
            self.logger.error('Error while deserializing peer certificate to discover intermediate certificates: %s', e)
            return

        try:
            authority_information_access = cert.extensions.get_extension_for_oid(
                ExtensionOID.AUTHORITY_INFORMATION_ACCESS
            )
        except ExtensionNotFound:
            self.logger.debug(
                'No Authority Information Access extension found, skipping discovery of intermediate certificates'
            )
            return

        for access_description in authority_information_access.value:
            if access_description.access_method != AuthorityInformationAccessOID.CA_ISSUERS:
                continue

            uri = access_description.access_location.value

            # Assume HTTP for now
            try:
                response = requests.get(uri)  # SKIP_HTTP_VALIDATION
            except Exception as e:
                self.logger.error('Error fetching intermediate certificate from `%s`: %s', uri, e)
                continue
            else:
                intermediate_cert = response.content

            certs.append(intermediate_cert)
            self.load_intermediate_certs(intermediate_cert, certs)
        return certs

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()

            # Enables HostHeaderSSLAdapter
            # https://toolbelt.readthedocs.io/en/latest/adapters.html#hostheaderssladapter
            if self.tls_use_host_header:
                self._session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
            # Enable Unix Domain Socket (UDS) support.
            # See: https://github.com/msabramo/requests-unixsocket
            self._session.mount('{}://'.format(UDS_SCHEME), requests_unixsocket.UnixAdapter())

            # Attributes can't be passed to the constructor
            for option, value in iteritems(self.options):
                setattr(self._session, option, value)

        return self._session

    def handle_auth_token(self, **request):
        if self.auth_token_handler is not None:
            self.auth_token_handler.poll(**request)

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

    if '*' in no_proxy_uris:
        # A single * character is supported, which matches all hosts, and effectively disables the proxy.
        # See: https://curl.haxx.se/libcurl/c/CURLOPT_NOPROXY.html
        return True

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
            if no_proxy_uri.startswith((".", "*.")):
                # Support wildcard subdomain; treat as leading dot "."
                # e.g. "*.example.domain" as ".example.domain"
                dot_no_proxy_uri = no_proxy_uri.lstrip("*")
            else:
                # Used for matching subdomains.
                dot_no_proxy_uri = ".{}".format(no_proxy_uri)
            if no_proxy_uri == parsed_uri or parsed_uri.endswith(dot_no_proxy_uri):
                return True
    return False


def create_basic_auth(config):
    # Since this is the default case, only activate when all fields are explicitly set
    if config['username'] and config['password']:
        if config['use_legacy_auth_encoding']:
            return config['username'], config['password']
        else:
            return ensure_bytes(config['username']), ensure_bytes(config['password'])


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


def create_auth_token_handler(config):
    if not isinstance(config, dict):
        raise ConfigurationError('The `auth_token` field must be a mapping')
    elif 'reader' not in config or 'writer' not in config:
        raise ConfigurationError('The `auth_token` field must define both `reader` and `writer` settings')

    config = deepcopy(config)

    reader_config = config['reader']
    if not isinstance(reader_config, dict):
        raise ConfigurationError('The `reader` settings of field `auth_token` must be a mapping')

    writer_config = config['writer']
    if not isinstance(writer_config, dict):
        raise ConfigurationError('The `writer` settings of field `auth_token` must be a mapping')

    reader_type = reader_config.pop('type', '')
    if not isinstance(reader_type, str):
        raise ConfigurationError('The reader `type` of field `auth_token` must be a string')
    elif not reader_type:
        raise ConfigurationError('The reader `type` of field `auth_token` is required')
    elif reader_type not in AUTH_TOKEN_READERS:
        raise ConfigurationError(
            'Unknown `auth_token` reader type, must be one of: {}'.format(', '.join(sorted(AUTH_TOKEN_READERS)))
        )

    writer_type = writer_config.pop('type', '')
    if not isinstance(writer_type, str):
        raise ConfigurationError('The writer `type` of field `auth_token` must be a string')
    elif not writer_type:
        raise ConfigurationError('The writer `type` of field `auth_token` is required')
    elif writer_type not in AUTH_TOKEN_WRITERS:
        raise ConfigurationError(
            'Unknown `auth_token` writer type, must be one of: {}'.format(', '.join(sorted(AUTH_TOKEN_WRITERS)))
        )

    reader = AUTH_TOKEN_READERS[reader_type](reader_config)
    writer = AUTH_TOKEN_WRITERS[writer_type](writer_config)

    return AuthTokenHandler(reader, writer)


class AuthTokenHandler(object):
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    def poll(self, **request):
        token = self.reader.read(**request)
        if token is not None:
            self.writer.write(token, **request)


class AuthTokenFileReader(object):
    def __init__(self, config):
        self._path = config.get('path', '')
        if not isinstance(self._path, str):
            raise ConfigurationError('The `path` setting of `auth_token` reader must be a string')
        elif not self._path:
            raise ConfigurationError('The `path` setting of `auth_token` reader is required')

        self._pattern = config.get('pattern')
        if self._pattern is not None:
            if not isinstance(self._pattern, str):
                raise ConfigurationError('The `pattern` setting of `auth_token` reader must be a string')
            else:
                self._pattern = re.compile(self._pattern)
                if self._pattern.groups != 1:
                    raise ValueError(
                        'The pattern `{}` setting of `auth_token` reader must define exactly one group'.format(
                            self._pattern.pattern
                        )
                    )

        # Cache all updates just in case
        self._token = None

    def read(self, **request):
        if self._token is None or 'error' in request:
            with open(self._path, 'r', encoding='utf-8') as f:
                content = f.read()

            if self._pattern is None:
                self._token = content.strip()
            else:
                match = self._pattern.search(content)
                if not match:
                    raise ValueError(
                        'The pattern `{}` does not match anything in file: {}'.format(self._pattern.pattern, self._path)
                    )

                self._token = match.group(1)

            return self._token


class DCOSAuthTokenReader(object):
    def __init__(self, config):
        self._login_url = config.get('login_url', '')
        if not isinstance(self._login_url, str):
            raise ConfigurationError('The `login_url` setting of DC/OS auth token reader must be a string')
        elif not self._login_url:
            raise ConfigurationError('The `login_url` setting of DC/OS auth token reader is required')

        self._service_account = config.get('service_account', '')
        if not isinstance(self._service_account, str):
            raise ConfigurationError('The `service_account` setting of DC/OS auth token reader must be a string')
        elif not self._service_account:
            raise ConfigurationError('The `service_account` setting of DC/OS auth token reader is required')

        self._private_key_path = config.get('private_key_path', '')
        if not isinstance(self._private_key_path, str):
            raise ConfigurationError('The `private_key_path` setting of DC/OS auth token reader must be a string')
        elif not self._private_key_path:
            raise ConfigurationError('The `private_key_path` setting of DC/OS auth token reader is required')

        self._expiration = config.get('expiration', 300)  # default to 5 minutes
        if not isinstance(self._expiration, int):
            raise ConfigurationError('The `expiration` setting of DC/OS auth token reader must be an integer')

        self._token = None

    def read(self, **request):
        if self._token is None or 'error' in request:
            with open(self._private_key_path, 'rb') as f:
                global default_backend
                if default_backend is None:
                    from cryptography.hazmat.backends import default_backend

                global serialization
                if serialization is None:
                    from cryptography.hazmat.primitives import serialization

                global jwt
                if jwt is None:
                    import jwt

                private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

                serialized_private = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )

                exp = int(get_timestamp() + self._expiration)

                encoded = jwt.encode({'uid': self._service_account, 'exp': exp}, serialized_private, algorithm='RS256')

                headers = {'Content-type': 'application/json'}
                r = requests.post(
                    url=self._login_url,
                    json={'uid': self._service_account, 'token': encoded, 'exp': exp},
                    headers=headers,
                    verify=False,
                )
                r.raise_for_status()

                self._token = r.json().get('token')

            return self._token


class AuthTokenHeaderWriter(object):
    DEFAULT_PLACEHOLDER = '<TOKEN>'

    def __init__(self, config):
        self._name = config.get('name', '')
        if not isinstance(self._name, str):
            raise ConfigurationError('The `name` setting of `auth_token` writer must be a string')
        elif not self._name:
            raise ConfigurationError('The `name` setting of `auth_token` writer is required')

        self._value = config.get('value', self.DEFAULT_PLACEHOLDER)
        if not isinstance(self._value, str):
            raise ConfigurationError('The `value` setting of `auth_token` writer must be a string')

        self._placeholder = config.get('placeholder', self.DEFAULT_PLACEHOLDER)
        if not isinstance(self._placeholder, str):
            raise ConfigurationError('The `placeholder` setting of `auth_token` writer must be a string')
        elif not self._placeholder:
            raise ConfigurationError('The `placeholder` setting of `auth_token` writer cannot be an empty string')
        elif self._placeholder not in self._value:
            raise ConfigurationError(
                'The `value` setting of `auth_token` writer does not contain the placeholder string `{}`'.format(
                    self._placeholder
                )
            )

    def write(self, token, **request):
        request['default_options']['headers'][self._name] = self._value.replace(self._placeholder, token, 1)


AUTH_TOKEN_READERS = {
    'file': AuthTokenFileReader,
    'dcos_auth': DCOSAuthTokenReader,
}
AUTH_TOKEN_WRITERS = {'header': AuthTokenHeaderWriter}


def is_uds_url(url):
    # type: (str) -> bool
    parsed = urlparse(url)
    return parsed.scheme == UDS_SCHEME


def quote_uds_url(url):
    # type: (str) -> str
    """
    Automatically convert an URL like 'unix:///var/run/docker.sock/info' to 'unix://%2Fvar%2Frun%2Fdocker.sock/info'.

    For user experience purposes, since `requests-unixsocket` only accepts the latter form.
    """
    parsed = urlparse(url)

    # When passing an UDS path URL, `netloc` is empty and `path` contains everything that's after '://'.
    # We want to extract the socket path from the URL path, and percent-encode it, and set it as the `netloc`.
    # For now we assume that UDS paths end in '.sock'. This is by far the most common convention.
    uds_path_head, has_dot_sock, path = parsed.path.partition('.sock')
    if not has_dot_sock:
        return url

    uds_path = '{}.sock'.format(uds_path_head)
    netloc = quote(uds_path, safe='')
    parsed = parsed._replace(netloc=netloc, path=path)

    return urlunparse(parsed)


# For documentation generation
# TODO: use an enum and remove STANDARD_FIELDS when mkdocstrings supports it
class StandardFields(object):
    pass


if not PY2:
    StandardFields.__doc__ = '\n'.join('- `{}`'.format(field) for field in STANDARD_FIELDS)
