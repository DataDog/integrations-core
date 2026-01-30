# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
import os
import re
import socket
import warnings
from collections import ChainMap
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from urllib.parse import quote, unquote, urlparse, urlunparse

import httpx
import lazy_loader
from binary import KIBIBYTE
from urllib3.exceptions import InsecureRequestWarning
from wrapt import ObjectProxy

from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils import _http_utils

from .common import ensure_bytes, ensure_unicode
from .headers import get_default_headers, update_headers
from .time import get_timestamp
from .tls import SUPPORTED_PROTOCOL_VERSIONS, TlsConfig, create_ssl_context

# See Performance Optimizations in this package's README.md.
httpx_gssapi = lazy_loader.load('httpx_gssapi')
httpx_ntlm = lazy_loader.load('httpx_ntlm')
authlib = lazy_loader.load('authlib')
jwt = lazy_loader.load('jwt')
ipaddress = lazy_loader.load('ipaddress')

# We log instead of emit warnings for unintentionally insecure HTTPS requests
warnings.simplefilter('ignore', InsecureRequestWarning)

LOGGER = logging.getLogger(__file__)

# The timeout should be slightly larger than a multiple of 3,
# which is the default TCP packet retransmission window. See:
# https://tools.ietf.org/html/rfc2988
DEFAULT_TIMEOUT = 10

DEFAULT_EXPIRATION = 300

# 16 KiB seems optimal, and is also the standard chunk size of the Bittorrent protocol:
# https://www.bittorrent.org/beps/bep_0003.html
DEFAULT_CHUNK_SIZE = 16

STANDARD_FIELDS = {
    'allow_redirects': True,
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
    'request_size': DEFAULT_CHUNK_SIZE,
    'skip_proxy': False,
    'timeout': DEFAULT_TIMEOUT,
    'use_legacy_auth_encoding': True,
    'username': None,
    **TlsConfig().__dict__,  # This will include all TLS-related fields
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


def create_socket_connection(hostname, port=443, sock_type=socket.SOCK_STREAM, timeout=10):
    """See: https://github.com/python/cpython/blob/40ee9a3640d702bce127e9877c82a99ce817f0d1/Lib/socket.py#L691"""
    err = None
    try:
        for res in socket.getaddrinfo(hostname, port, 0, sock_type):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                sock.settimeout(timeout)
                sock.connect(sa)
                # Break explicitly a reference cycle
                err = None
                return sock

            except socket.error as _:
                err = _
                if sock is not None:
                    sock.close()

        if err is not None:
            raise err
        else:
            raise socket.error('No valid addresses found, try checking your IPv6 connectivity')  # noqa: G
    except socket.gaierror as e:
        err_code, message = e.args
        if err_code == socket.EAI_NODATA or err_code == socket.EAI_NONAME:
            raise socket.error('Unable to resolve host, check your DNS: {}'.format(message))  # noqa: G

        raise


def get_tls_config_from_options(new_options):
    '''Extract TLS configuration from request options.'''
    tls_config = {}
    verify = new_options.get('verify')
    cert = new_options.get('cert')

    if isinstance(verify, str):
        tls_config["tls_verify"] = True
        tls_config["tls_ca_cert"] = verify
    elif isinstance(verify, bool):
        tls_config["tls_verify"] = verify
    elif verify is not None:
        raise TypeError(
            'Unexpected type for `verify` option. Expected bool or str, got {}.'.format(type(verify).__name__)
        )

    if isinstance(cert, str):
        tls_config["tls_cert"] = cert
    elif isinstance(cert, tuple) or isinstance(cert, list):
        if len(cert) != 2:
            raise TypeError(
                'Unexpected length for `cert` option. Expected a tuple of length 2, got {}.'.format(len(cert))
            )
        tls_config["tls_cert"] = cert[0]
        tls_config["tls_private_key"] = cert[1]
    elif cert is not None:
        raise TypeError('Unexpected type for `cert` option. Expected str or tuple, got {}.'.format(type(cert).__name__))
    return tls_config


def _build_httpx_transport(ssl_context, uds_path=None, tls_use_host_header=False):
    """
    Build httpx.HTTPTransport with SSL context and optional UDS support.

    Args:
        ssl_context: SSL context to use for HTTPS connections
        uds_path: Optional Unix Domain Socket path
        tls_use_host_header: If True, use Host header for SNI (httpx doesn't have direct equivalent)

    Returns:
        httpx.HTTPTransport configured with the provided options
    """
    if uds_path:
        return httpx.HTTPTransport(uds=uds_path, verify=ssl_context)

    # Note: httpx doesn't have a direct equivalent to HostHeaderSSLAdapter
    # The tls_use_host_header functionality may need to be handled differently
    # or may not be needed with httpx's implementation
    return httpx.HTTPTransport(verify=ssl_context)


class ResponseWrapper(ObjectProxy):
    def __init__(self, response, default_chunk_size):
        super(ResponseWrapper, self).__init__(response)

        # See https://github.com/psf/requests/pull/5942
        self.__default_chunk_size = default_chunk_size

    def iter_content(self, chunk_size=None, decode_unicode=False):
        if chunk_size is None:
            chunk_size = self.__default_chunk_size

        # httpx uses iter_bytes() for binary content and iter_text() for decoded content
        if decode_unicode:
            # For httpx, iter_text() returns strings, chunk_size is in chars not bytes
            return self.__wrapped__.iter_text(chunk_size=chunk_size)
        return self.__wrapped__.iter_bytes(chunk_size=chunk_size)

    def iter_lines(self, chunk_size=None, decode_unicode=False, delimiter=None):
        if chunk_size is None:
            chunk_size = self.__default_chunk_size

        # httpx's iter_lines() doesn't support chunk_size or delimiter parameters
        # It yields lines directly
        return self.__wrapped__.iter_lines()

    def __enter__(self):
        return self


class RequestsWrapper(object):
    __slots__ = (
        '_session',
        '_https_adapters',
        'tls_use_host_header',
        'ignore_tls_warning',
        'log_requests',
        'logger',
        'no_proxy_uris',
        'options',
        'persist_connections',
        'request_hooks',
        'auth_token_handler',
        'request_size',
        'tls_protocols_allowed',
        'tls_config',
    )

    def __init__(self, instance, init_config, remapper=None, logger=None, session=None):
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
        config = {field: instance.get(field, value) for field, value in default_fields.items()}

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

        for remapped_field, data in remapper.items():
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

        # https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
        connect_timeout = read_timeout = float(config['timeout'])
        if config['connect_timeout'] is not None:
            connect_timeout = float(config['connect_timeout'])

        if config['read_timeout'] is not None:
            read_timeout = float(config['read_timeout'])

        # https://requests.readthedocs.io/en/latest/user/quickstart/#custom-headers
        # https://requests.readthedocs.io/en/latest/user/advanced/#header-ordering
        headers = get_default_headers()
        if config['headers']:
            headers.clear()
            update_headers(headers, config['headers'])

        if config['extra_headers']:
            update_headers(headers, config['extra_headers'])

        # https://toolbelt.readthedocs.io/en/latest/adapters.html#hostheaderssladapter
        self.tls_use_host_header = is_affirmative(config['tls_use_host_header']) and 'Host' in headers

        # https://requests.readthedocs.io/en/latest/user/authentication/
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

        allow_redirects = is_affirmative(config['allow_redirects'])

        # For TLS verification, we now rely on the TLS context wrapper
        # but still need to set verify for requests compatibility
        verify = True
        if isinstance(config['tls_ca_cert'], str):
            verify = config['tls_ca_cert']
        elif not is_affirmative(config['tls_verify']):
            verify = False

        # https://requests.readthedocs.io/en/latest/user/advanced/#client-side-certificates
        cert = None
        if isinstance(config['tls_cert'], str):
            if isinstance(config['tls_private_key'], str):
                cert = (config['tls_cert'], config['tls_private_key'])
            else:
                cert = config['tls_cert']

        # https://requests.readthedocs.io/en/latest/user/advanced/#proxies
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
                # https://github.com/psf/requests/issues/5000
                if 'no_proxy' in proxies:
                    no_proxy_uris = proxies.pop('no_proxy')

                    if isinstance(no_proxy_uris, str):
                        no_proxy_uris = no_proxy_uris.replace(';', ',').split(',')
            else:
                proxies = None

        # Default options
        # httpx uses httpx.Timeout object instead of tuple
        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,  # Use read_timeout for write operations as well
            pool=None,  # No timeout for acquiring a connection from the pool
        )

        self.options = {
            'auth': auth,
            'cert': cert,
            'headers': headers,
            'proxies': proxies,
            'timeout': timeout,
            'verify': verify,
            'allow_redirects': allow_redirects,
        }

        # For manual parsing until `requests` properly handles `no_proxy`
        self.no_proxy_uris = no_proxy_uris

        # Ignore warnings for lack of SSL validation
        self.ignore_tls_warning = is_affirmative(config['tls_ignore_warning'])

        self.request_size = int(float(config['request_size']) * KIBIBYTE)

        self.tls_protocols_allowed = []
        for protocol in config['tls_protocols_allowed']:
            if protocol in SUPPORTED_PROTOCOL_VERSIONS:
                self.tls_protocols_allowed.append(protocol)
            else:
                self.logger.warning('Unknown protocol `%s` configured, ignoring it.', protocol)

        # For connection and cookie persistence, if desired. See:
        # https://en.wikipedia.org/wiki/HTTP_persistent_connection#Advantages
        # https://requests.readthedocs.io/en/latest/user/advanced/#session-objects
        # https://requests.readthedocs.io/en/latest/user/advanced/#keep-alive
        self.persist_connections = self.tls_use_host_header or is_affirmative(config['persist_connections'])
        self._session = session

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

        self.tls_config = {key: value for key, value in config.items() if key.startswith('tls_')}
        self._https_adapters = {}

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
            self.logger.debug('Sending %s request to %s', method.upper(), url)

        if self.no_proxy_uris and should_bypass_proxy(url, self.no_proxy_uris):
            options.setdefault('proxies', PROXY_SETTINGS_DISABLED)

        persist = options.pop('persist', None)
        if persist is None:
            persist = self.persist_connections

        new_options = ChainMap(options, self.options)

        if url.startswith('https') and not self.ignore_tls_warning and not new_options['verify']:
            self.logger.debug('An unverified HTTPS request is being made to %s', url)

        extra_headers = options.pop('extra_headers', None)
        if extra_headers is not None:
            new_options['headers'] = new_options['headers'].copy()
            new_options['headers'].update(extra_headers)

        if is_uds_url(url):
            persist = True  # UDS support is only enabled on the shared session.
            # For httpx, extract the socket path and convert the URL
            # httpx doesn't use unix:// scheme, it uses a UDS transport parameter
            parsed = urlparse(url)
            # The socket path is percent-encoded in the netloc
            socket_path = unquote(parsed.netloc) if parsed.netloc else None
            if not socket_path:
                # Try to extract from the path (e.g., unix:///path/to/socket)
                uds_path_head, has_dot_sock, remaining_path = parsed.path.partition('.sock')
                if has_dot_sock:
                    socket_path = f'{uds_path_head}.sock'
                    parsed = parsed._replace(path=remaining_path)

            self._current_uds_path = socket_path
            # Convert to http://localhost for httpx (it uses the transport to know it's UDS)
            url = 'http://localhost' + parsed.path
            if parsed.query:
                url += '?' + parsed.query

        self.handle_auth_token(method=method, url=url, default_options=self.options)

        with ExitStack() as stack:
            for hook in self.request_hooks:
                stack.enter_context(hook())

            session = self.session if persist else self._create_session()
            if url.startswith('https'):
                self._mount_https_adapter(session, ChainMap(get_tls_config_from_options(new_options), self.tls_config))
            request_method = getattr(session, method)

            if self.auth_token_handler:
                try:
                    response = self.make_request_aia_chasing(request_method, method, url, new_options, persist)
                    response.raise_for_status()
                except Exception as e:
                    self.logger.debug('Renewing auth token, as an error occurred: %s', e)
                    self.handle_auth_token(method=method, url=url, default_options=self.options, error=str(e))
                    response = self.make_request_aia_chasing(request_method, method, url, new_options, persist)
            else:
                response = self.make_request_aia_chasing(request_method, method, url, new_options, persist)

            return ResponseWrapper(response, self.request_size)

    def make_request_aia_chasing(self, request_method, method, url, new_options, persist):
        try:
            response = request_method(url, **new_options)
        except (httpx.ConnectError, httpx.RemoteProtocolError) as e:
            # For httpx, SSL errors come as ConnectError or RemoteProtocolError
            # Attempt to fetch intermediate certs if this looks like an SSL issue
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname
            port = parsed_url.port
            certs = self.fetch_intermediate_certs(hostname, port)
            if not certs:
                raise e
            session = self.session if persist else self._create_session()
            if parsed_url.scheme == "https":
                self._configure_https_transport(
                    session, ChainMap({'tls_intermediate_ca_certs': certs}, self.tls_config)
                )
            request_method = getattr(session, method)
            response = request_method(url, **new_options)
        return response

    def fetch_intermediate_certs(self, hostname, port=443):
        # TODO: prefer stdlib implementation when available, see https://bugs.python.org/issue18617
        certs = []

        try:
            sock = create_socket_connection(hostname, port)
        except Exception as e:
            self.logger.error('Error occurred while connecting to socket to discover intermediate certificates: %s', e)
            return certs

        with sock:
            try:
                context = create_ssl_context(ChainMap({'tls_verify': False}, self.tls_config))

                with context.wrap_socket(sock, server_hostname=hostname) as secure_sock:
                    der_cert = secure_sock.getpeercert(binary_form=True)
                    protocol_version = secure_sock.version()
                    if protocol_version and protocol_version not in self.tls_protocols_allowed:
                        raise Exception(
                            'Protocol version `{}` not in the allowed list {}'.format(
                                protocol_version, self.tls_protocols_allowed
                            )
                        )
            except Exception as e:
                self.logger.error('Error occurred while getting cert to discover intermediate certificates: %s', e)
                return certs

        self.load_intermediate_certs(der_cert, certs)
        return certs

    def load_intermediate_certs(self, der_cert, certs):
        # https://tools.ietf.org/html/rfc3280#section-4.2.2.1
        # https://tools.ietf.org/html/rfc5280#section-5.2.7
        try:
            cert = _http_utils.cryptography_x509_load_certificate(der_cert)
        except Exception as e:
            self.logger.error('Error while deserializing peer certificate to discover intermediate certificates: %s', e)
            return

        try:
            authority_information_access = cert.extensions.get_extension_for_oid(
                _http_utils.cryptography_x509_ExtensionOID.AUTHORITY_INFORMATION_ACCESS
            )
        except _http_utils.cryptography_x509_ExtensionNotFound:
            self.logger.debug(
                'No Authority Information Access extension found, skipping discovery of intermediate certificates'
            )
            return

        for access_description in authority_information_access.value:
            if (
                access_description.access_method
                != _http_utils.cryptography_x509_AuthorityInformationAccessOID.CA_ISSUERS
            ):
                continue

            uri = access_description.access_location.value

            # Assume HTTP for now
            try:
                response = self.get(uri)  # SKIP_HTTP_VALIDATION
            except Exception as e:
                self.logger.error('Error fetching intermediate certificate from `%s`: %s', uri, e)
                continue
            else:
                intermediate_cert = response.content

            certs.append(intermediate_cert)
            self.load_intermediate_certs(intermediate_cert, certs)
        return certs

    def _create_session(self):
        """
        Initializes httpx.Client and configures it with options coming from user's config.

        Note: httpx.Client takes most options as constructor parameters rather than
        setting them as attributes after initialization.
        """
        # Extract UDS path if it was set during _request (for UDS URLs)
        uds_path = getattr(self, '_current_uds_path', None)

        # Build transport - SSL context will be configured separately via _mount_https_adapter
        # For now, create a basic transport
        transport = httpx.HTTPTransport(uds=uds_path) if uds_path else None

        # Create httpx.Client with options from self.options
        # Note: Not all options transfer directly, httpx uses different parameter names
        client = httpx.Client(
            transport=transport,
            timeout=self.options.get('timeout'),
            headers=self.options.get('headers'),
            auth=self.options.get('auth'),
            proxies=self.options.get('proxies'),
            verify=self.options.get('verify', True),
            cert=self.options.get('cert'),
            follow_redirects=self.options.get('allow_redirects', True),
        )
        return client

    @property
    def session(self):
        if self._session is None:
            # Create a new httpx.Client if it doesn't exist
            # Note: httpx configures transport with SSL context at creation time,
            # not through mounting adapters like requests
            self._session = self._create_session()
            # Configure HTTPS transport with TLS config
            self._configure_https_transport(self._session, self.tls_config)
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

    def _configure_https_transport(self, client, tls_config):
        """
        Configure httpx.Client with HTTPS transport using the provided TLS config.

        Note: With httpx, we can't "mount" adapters like with requests.
        Instead, we need to recreate the client with a new transport that has
        the correct SSL context. However, this is typically done at client creation time.
        For now, we'll update the client's transport if needed.
        """
        # Reuse existing transport if it matches the TLS config
        tls_config_key = TlsConfig(**tls_config)
        if tls_config_key in self._https_adapters:
            # Reuse cached transport
            client._transport = self._https_adapters[tls_config_key]
            return

        context = create_ssl_context(tls_config)

        # Extract UDS path if set
        uds_path = getattr(self, '_current_uds_path', None)

        # Build transport with SSL context
        transport = _build_httpx_transport(context, uds_path, self.tls_use_host_header)

        # Cache the transport for reuse
        self._https_adapters[tls_config_key] = transport

        # Update the client's transport
        # Note: This is a bit of a hack as httpx clients are not designed to have
        # their transport swapped out after creation
        client._transport = transport


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
    parsed_uri_parts = urlparse(url)
    parsed_uri = parsed_uri_parts.hostname

    if '*' in no_proxy_uris:
        # A single * character is supported, which matches all hosts, and effectively disables the proxy.
        # See: https://curl.haxx.se/libcurl/c/CURLOPT_NOPROXY.html
        return True

    if parsed_uri_parts.scheme == "unix":
        # Unix domain sockets semantically do not make sense to proxy
        return True

    for no_proxy_uri in no_proxy_uris:
        try:
            # If no_proxy_uri is an IP or IP CIDR.
            # A ValueError is raised if address does not represent a valid IPv4 or IPv6 address.
            ip_network = ipaddress.ip_network(ensure_unicode(no_proxy_uri))
            ip_address = ipaddress.ip_address(ensure_unicode(parsed_uri))
            if ip_address in ip_network:
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
    if config['username'] is not None and config['password'] is not None:
        # httpx.BasicAuth handles both str and bytes
        if config['use_legacy_auth_encoding']:
            return httpx.BasicAuth(config['username'], config['password'])
        else:
            # Convert to bytes if needed
            username = ensure_bytes(config['username'])
            password = ensure_bytes(config['password'])
            # httpx expects strings, so decode back
            return httpx.BasicAuth(
                username.decode('utf-8') if isinstance(username, bytes) else username,
                password.decode('utf-8') if isinstance(password, bytes) else password,
            )


def create_digest_auth(config):
    return httpx.DigestAuth(config['username'], config['password'])


def create_ntlm_auth(config):
    return httpx_ntlm.HttpNtlmAuth(config['ntlm_domain'], config['password'])


def create_kerberos_auth(config):
    # httpx-gssapi uses different constants than requests-kerberos
    # Map them appropriately
    try:
        KERBEROS_STRATEGIES['required'] = httpx_gssapi.REQUIRED
        KERBEROS_STRATEGIES['optional'] = httpx_gssapi.OPTIONAL
        KERBEROS_STRATEGIES['disabled'] = httpx_gssapi.DISABLED
    except AttributeError:
        # httpx-gssapi might use different attribute names
        # Use boolean for now as fallback
        KERBEROS_STRATEGIES['required'] = True
        KERBEROS_STRATEGIES['optional'] = False
        KERBEROS_STRATEGIES['disabled'] = False

    # For convenience
    if config['kerberos_auth'] is None or is_affirmative(config['kerberos_auth']):
        config['kerberos_auth'] = 'required'

    if config['kerberos_auth'] not in KERBEROS_STRATEGIES:
        raise ConfigurationError(
            'Invalid Kerberos strategy `{}`, must be one of: {}'.format(
                config['kerberos_auth'], ' | '.join(KERBEROS_STRATEGIES)
            )
        )

    # httpx-gssapi uses HTTPSPNEGOAuth instead of HTTPKerberosAuth
    return httpx_gssapi.HTTPSPNEGOAuth(
        mutual_authentication=KERBEROS_STRATEGIES[config['kerberos_auth']],
        delegate=is_affirmative(config['kerberos_delegate']),
        opportunistic_auth=is_affirmative(config['kerberos_force_initiate']),
        target_name=config['kerberos_hostname'],
        # Note: httpx-gssapi may not support principal parameter directly
    )


class HTTPXAWSAuth(httpx.Auth):
    """
    Custom httpx.Auth adapter for AWS authentication.
    Wraps the BotoAWSRequestsAuth to work with httpx.
    """

    def __init__(self, aws_host, aws_region, aws_service):
        self._aws_auth = _http_utils.BotoAWSRequestsAuth(
            aws_host=aws_host, aws_region=aws_region, aws_service=aws_service
        )

    def auth_flow(self, request):
        # Convert httpx.Request to a format that BotoAWSRequestsAuth can sign
        # BotoAWSRequestsAuth expects a requests-style request
        # We need to create a minimal request-like object
        class RequestsLikeRequest:
            def __init__(self, httpx_request):
                self.url = str(httpx_request.url)
                self.method = httpx_request.method
                self.headers = dict(httpx_request.headers)
                self.body = httpx_request.content

        requests_like = RequestsLikeRequest(request)
        # Apply AWS auth (modifies headers)
        self._aws_auth(requests_like)
        # Update httpx request headers with signed headers
        request.headers.update(requests_like.headers)
        yield request


def create_aws_auth(config):
    for setting in ('aws_host', 'aws_region', 'aws_service'):
        if not config[setting]:
            raise ConfigurationError('AWS auth requires the setting `{}`'.format(setting))

    return HTTPXAWSAuth(aws_host=config['aws_host'], aws_region=config['aws_region'], aws_service=config['aws_service'])


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
            self._fetch_options['auth'] = httpx.BasicAuth(self._client_id, self._client_secret)
        else:
            self._fetch_options['client_id'] = self._client_id
            self._fetch_options['client_secret'] = self._client_secret

        self._options = config.get('options', {})
        if isinstance(self._options, dict):
            for key, value in self._options.items():
                self._fetch_options[key] = value

        self._token = None
        self._expiration = None

    def read(self, **request):
        if self._token is None or get_timestamp() >= self._expiration or 'error' in request:
            # Use authlib instead of requests_oauthlib for httpx compatibility
            from authlib.integrations.httpx_client import OAuth2Client

            oauth = OAuth2Client(client_id=self._client_id, client_secret=self._client_secret)
            response = oauth.fetch_token(**self._fetch_options)

            # https://www.rfc-editor.org/rfc/rfc6749#section-5.2
            if 'error' in response:
                raise Exception('OAuth2 client credentials grant error: {}'.format(response['error']))

            # https://www.rfc-editor.org/rfc/rfc6749#section-4.4.3
            self._token = response['access_token']
            self._expiration = get_timestamp()
            try:
                # According to https://www.rfc-editor.org/rfc/rfc6749#section-5.1, the `expires_in` field is optional
                self._expiration += _parse_expires_in(response.get('expires_in'))
            except TypeError:
                LOGGER.debug(
                    'The `expires_in` field of the OAuth2 response is not a number, defaulting to %s',
                    DEFAULT_EXPIRATION,
                )
                self._expiration += DEFAULT_EXPIRATION
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
                private_key = _http_utils.cryptography_serialization.load_pem_private_key(f.read(), password=None)

                serialized_private = private_key.private_bytes(
                    encoding=_http_utils.cryptography_serialization.Encoding.PEM,
                    format=_http_utils.cryptography_serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=_http_utils.cryptography_serialization.NoEncryption(),
                )

                exp = int(get_timestamp() + self._expiration)

                encoded = jwt.encode({'uid': self._service_account, 'exp': exp}, serialized_private, algorithm='RS256')

                headers = {'Content-type': 'application/json'}
                # Use httpx instead of requests
                with httpx.Client(verify=False) as client:
                    r = client.post(
                        url=self._login_url,
                        json={'uid': self._service_account, 'token': encoded, 'exp': exp},
                        headers=headers,
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
    'oauth': AuthTokenOAuthReader,
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


def _parse_expires_in(token_expiration):
    if isinstance(token_expiration, int) or isinstance(token_expiration, float):
        return token_expiration
    if isinstance(token_expiration, str):
        try:
            token_expiration = int(token_expiration)
        except ValueError:
            LOGGER.debug('Could not convert %s to an integer', token_expiration)
    else:
        LOGGER.debug('Unexpected type for `expires_in`: %s.', type(token_expiration))
        token_expiration = None

    return token_expiration


# For documentation generation
# TODO: use an enum and remove STANDARD_FIELDS when mkdocstrings supports it
class StandardFields(object):
    pass


StandardFields.__doc__ = '\n'.join('- `{}`'.format(field) for field in STANDARD_FIELDS)
