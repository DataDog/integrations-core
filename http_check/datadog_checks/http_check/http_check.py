# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

# stdlib
from datetime import datetime
import _strptime # noqa
import os.path
import re
import socket
import ssl
import time
import warnings
from urlparse import urlparse

# 3rd party
import requests
from requests.adapters import HTTPAdapter
from requests.packages import urllib3
from requests.packages.urllib3.util import ssl_
from requests.packages.urllib3.exceptions import InsecureRequestWarning, SecurityWarning
from requests.packages.urllib3.packages.ssl_match_hostname import match_hostname
from requests_ntlm import HttpNtlmAuth

# project
from datadog_checks.base.checks import NetworkCheck, Status
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.utils.headers import headers as agent_headers

DEFAULT_EXPECTED_CODE = "(1|2|3)\d\d"
CONTENT_LENGTH = 200

DATA_METHODS = ['POST', 'PUT', 'DELETE', 'PATCH']


class WeakCiphersHTTPSConnection(urllib3.connection.VerifiedHTTPSConnection):

    SUPPORTED_CIPHERS = (
        'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:'
        'ECDH+HIGH:DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:'
        'RSA+3DES:ECDH+RC4:DH+RC4:RSA+RC4:!aNULL:!eNULL:!EXP:-MD5:RSA+RC4+MD5'
    )

    def __init__(self, host, port, ciphers=None, **kwargs):
        self.ciphers = ciphers if ciphers is not None else self.SUPPORTED_CIPHERS
        super(WeakCiphersHTTPSConnection, self).__init__(host, port, **kwargs)

    def connect(self):
        # Add certificate verification
        conn = self._new_conn()

        resolved_cert_reqs = ssl_.resolve_cert_reqs(self.cert_reqs)
        resolved_ssl_version = ssl_.resolve_ssl_version(self.ssl_version)

        hostname = self.host
        if getattr(self, '_tunnel_host', None):
            # _tunnel_host was added in Python 2.6.3
            # (See:
            # http://hg.python.org/cpython/rev/0f57b30a152f)
            #
            # However this check is still necessary in 2.7.x

            self.sock = conn
            # Calls self._set_hostport(), so self.host is
            # self._tunnel_host below.
            self._tunnel()
            # Mark this connection as not reusable
            self.auto_open = 0

            # Override the host with the one we're requesting data from.
            hostname = self._tunnel_host

        # Wrap socket using verification with the root certs in trusted_root_certs
        self.sock = ssl_.ssl_wrap_socket(conn, self.key_file, self.cert_file,
                                         cert_reqs=resolved_cert_reqs,
                                         ca_certs=self.ca_certs,
                                         server_hostname=hostname,
                                         ssl_version=resolved_ssl_version,
                                         ciphers=self.ciphers)

        if self.assert_fingerprint:
            ssl_.assert_fingerprint(self.sock.getpeercert(binary_form=True), self.assert_fingerprint)
        elif resolved_cert_reqs != ssl.CERT_NONE \
                and self.assert_hostname is not False:
            cert = self.sock.getpeercert()
            if not cert.get('subjectAltName', ()):
                warnings.warn((
                    'Certificate has no `subjectAltName`, falling back to check for a `commonName` for now. '
                    'This feature is being removed by major browsers and deprecated by RFC 2818. '
                    '(See https://github.com/shazow/urllib3/issues/497 for details.)'),
                    SecurityWarning
                )
            match_hostname(cert, self.assert_hostname or hostname)

        self.is_verified = (resolved_cert_reqs == ssl.CERT_REQUIRED or self.assert_fingerprint is not None)


class WeakCiphersHTTPSConnectionPool(urllib3.connectionpool.HTTPSConnectionPool):

    ConnectionCls = WeakCiphersHTTPSConnection


class WeakCiphersPoolManager(urllib3.poolmanager.PoolManager):

    def _new_pool(self, scheme, host, port):
        if scheme == 'https':
            return WeakCiphersHTTPSConnectionPool(host, port, **(self.connection_pool_kw))
        return super(WeakCiphersPoolManager, self)._new_pool(scheme, host, port)


class WeakCiphersAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use TLS_RSA_WITH_RC4_128_MD5."""

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        # Rewrite of the
        # requests.adapters.HTTPAdapter.init_poolmanager method
        # to use WeakCiphersPoolManager instead of
        # urllib3's PoolManager
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = WeakCiphersPoolManager(num_pools=connections,
                                                  maxsize=maxsize, block=block, strict=True, **pool_kwargs)


def get_ca_certs_path():
    """
    Get a path to the trusted certificates of the system
    """
    """
    check is installed via pip to:
    Windows: embedded/lib/site-packages/datadog_checks/http_check
    Linux: embedded/lib/python2.7/site-packages/datadog_checks/http_check
    certificate is installed to   embedded/ssl/certs/cacert.pem

    walk up to embedded, and back down to ssl/certs to find the certificate file
    """

    ca_certs = []

    embedded_root = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.basename(embedded_root) == 'embedded':
            ca_certs.append(os.path.join(embedded_root, 'ssl', 'certs', 'cacert.pem'))
            break
        embedded_root = os.path.dirname(embedded_root)
    else:
        raise OSError('Unable to locate `embedded` directory. '
                      'Please specify ca_certs in your http yaml configuration file.')

    try:
        import tornado
    except ImportError:
        # if `tornado` is not present, simply ignore its certificates
        pass
    else:
        ca_certs.append(os.path.join(os.path.dirname(tornado.__file__), 'ca-certificates.crt'))

    ca_certs.append('/etc/ssl/certs/ca-certificates.crt')

    for f in ca_certs:
        if os.path.exists(f):
            return f
    return None


class HTTPCheck(NetworkCheck):
    SOURCE_TYPE_NAME = 'system'
    SC_STATUS = 'http.can_connect'
    SC_SSL_CERT = 'http.ssl_cert'

    def __init__(self, name, init_config, agentConfig, instances=None):
        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

        self.ca_certs = init_config.get('ca_certs', get_ca_certs_path())

    def _load_conf(self, instance):
        # Fetches the conf
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
        default_headers = _is_affirmative(instance.get("include_default_headers", True))
        if default_headers:
            headers = agent_headers(self.agentConfig)
        else:
            headers = {}
        headers.update(config_headers)
        url = instance.get('url')
        content_match = instance.get('content_match')
        reverse_content_match = _is_affirmative(instance.get('reverse_content_match', False))
        response_time = _is_affirmative(instance.get('collect_response_time', True))
        if not url:
            raise Exception("Bad configuration. You must specify a url")
        include_content = _is_affirmative(instance.get('include_content', False))
        disable_ssl_validation = _is_affirmative(instance.get('disable_ssl_validation', True))
        ssl_expire = _is_affirmative(instance.get('check_certificate_expiration', True))
        instance_ca_certs = instance.get('ca_certs', self.ca_certs)
        weakcipher = _is_affirmative(instance.get('weakciphers', False))
        ignore_ssl_warning = _is_affirmative(instance.get('ignore_ssl_warning', False))
        check_hostname = _is_affirmative(instance.get('check_hostname', True))
        skip_proxy = _is_affirmative(
            instance.get('skip_proxy', instance.get('no_proxy', False)))
        allow_redirects = _is_affirmative(instance.get('allow_redirects', True))

        return url, ntlm_domain, username, password, client_cert, client_key, method, data, http_response_status_code, \
            timeout, include_content, headers, response_time, content_match, reverse_content_match, tags, \
            disable_ssl_validation, ssl_expire, instance_ca_certs, weakcipher, check_hostname, ignore_ssl_warning, \
            skip_proxy, allow_redirects

    def _check(self, instance):
        addr, ntlm_domain, username, password, client_cert, client_key, method, data, http_response_status_code, \
            timeout, include_content, headers, response_time, content_match, reverse_content_match, tags, \
            disable_ssl_validation, ssl_expire, instance_ca_certs, weakcipher, check_hostname, ignore_ssl_warning, \
            skip_proxy, allow_redirects = self._load_conf(instance)

        start = time.time()

        def send_status_up(logMsg):
            self.log.debug(logMsg)
            service_checks.append((
                self.SC_STATUS, Status.UP, "UP"
            ))

        def send_status_down(loginfo, message):
            self.log.info(loginfo)
            if include_content:
                message += '\nContent: {}'.format(content[:CONTENT_LENGTH])
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                message
            ))

        service_checks = []
        try:
            parsed_uri = urlparse(addr)
            self.log.debug("Connecting to {}".format(addr))

            suppress_warning = False
            if disable_ssl_validation and parsed_uri.scheme == "https":
                explicit_validation = 'disable_ssl_validation' in instance
                if ignore_ssl_warning:
                    if explicit_validation:
                        suppress_warning = True
                else:
                    # Log if we're skipping SSL validation for HTTPS URLs
                    if explicit_validation:
                        self.log.debug("Skipping SSL certificate validation for {} based on configuration".format(addr))

                    # Emit a warning if disable_ssl_validation is not explicitly set and we're not ignoring warnings
                    else:
                        self.warning("Parameter disable_ssl_validation for {} is not explicitly set, "
                                     "defaults to true".format(addr))

            instance_proxy = self.get_instance_proxy(instance, addr)
            self.log.debug("Proxies used for {} - {}".format(addr, instance_proxy))

            auth = None
            if password is not None:
                if username is not None:
                    auth = (username, password)
                elif ntlm_domain is not None:
                    auth = HttpNtlmAuth(ntlm_domain, password)

            sess = requests.Session()
            sess.trust_env = False
            if weakcipher:
                base_addr = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
                sess.mount(base_addr, WeakCiphersAdapter())
                self.log.debug("Weak Ciphers will be used for {}. Supported Cipherlist: {}".format(
                               base_addr, WeakCiphersHTTPSConnection.SUPPORTED_CIPHERS))

            with warnings.catch_warnings():
                # Suppress warnings from urllib3 only if disable_ssl_validation is explicitly set to True
                #  and ignore_ssl_warning is True
                if suppress_warning:
                    warnings.simplefilter('ignore', InsecureRequestWarning)

                r = sess.request(method.upper(), addr, auth=auth, timeout=timeout, headers=headers,
                                 proxies=instance_proxy, allow_redirects=allow_redirects,
                                 verify=False if disable_ssl_validation else instance_ca_certs,
                                 json=data if method.upper() in DATA_METHODS and isinstance(data, dict) else None,
                                 data=data if method.upper() in DATA_METHODS and isinstance(data, basestring) else None,
                                 cert=(client_cert, client_key) if client_cert and client_key else None)

        except (socket.timeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            length = int((time.time() - start) * 1000)
            self.log.info("{} is DOWN, error: {}. Connection failed after {} ms".format(addr, str(e), length))
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "{}. Connection failed after {} ms".format(str(e), length)
            ))

        except socket.error as e:
            length = int((time.time() - start) * 1000)
            self.log.info("{} is DOWN, error: {}. Connection failed after {} ms".format(addr, repr(e), length))
            service_checks.append((
                self.SC_STATUS,
                Status.DOWN,
                "Socket error: {}. Connection failed after {} ms".format(repr(e), length)
            ))

        except Exception as e:
            length = int((time.time() - start) * 1000)
            self.log.error("Unhandled exception {}. Connection failed after {} ms".format(str(e), length))
            raise

        # Store tags in a temporary list so that we don't modify the global tags data structure
        tags_list = list(tags)
        # Only add the URL tag if it's not already present
        if not filter(re.compile('^url:').match, tags_list):
            tags_list.append('url:{}'.format(addr))

        # Only report this metric if the site is not down
        if response_time and not service_checks:
            # Stop the timer as early as possible
            running_time = time.time() - start
            self.gauge('network.http.response_time', running_time, tags=tags_list)

        # Check HTTP response status code
        if not (service_checks or re.match(http_response_status_code, str(r.status_code))):
            if http_response_status_code == DEFAULT_EXPECTED_CODE:
                expected_code = "1xx or 2xx or 3xx"
            else:
                expected_code = http_response_status_code

            message = "Incorrect HTTP return code for url {}. Expected {}, got {}.".format(
                      addr, expected_code, str(r.status_code))

            if include_content:
                message += '\nContent: {}'.format(r.content[:CONTENT_LENGTH])

            self.log.info(message)

            service_checks.append((self.SC_STATUS, Status.DOWN, message))

        if not service_checks:
            # Host is UP
            # Check content matching is set
            if content_match:
                # r.text is the response content decoded by `requests`, of type `unicode`
                content = r.text if type(content_match) is unicode else r.content
                if re.search(content_match, content, re.UNICODE):
                    if reverse_content_match:
                        send_status_down('{} is found in return content with the reverse_content_match option'
                                         .format(content_match),
                                         'Content "{}" found in response with the reverse_content_match'
                                         .format(content_match))
                    else:
                        send_status_up("{} is found in return content".format(content_match))

                else:
                    if reverse_content_match:
                        send_status_up("{} is not found in return content with the reverse_content_match option"
                                       .format(content_match))
                    else:
                        send_status_down("{} is not found in return content".format(content_match),
                                         'Content "{}" not found in response.'.format(content_match))

            else:
                send_status_up("{} is UP".format(addr))

        # Report status metrics as well
        if service_checks:
            can_status = 1 if service_checks[0][1] == "UP" else 0
            self.gauge('network.http.can_connect', can_status, tags=tags_list)

            # cant_connect is useful for top lists
            cant_status = 0 if service_checks[0][1] == "UP" else 1
            self.gauge('network.http.cant_connect', cant_status, tags=tags_list)

        if ssl_expire and parsed_uri.scheme == "https":
            status, days_left, msg = self.check_cert_expiration(instance, timeout, instance_ca_certs, check_hostname,
                                                                client_cert, client_key)

            tags_list = list(tags)
            tags_list.append('url:{}'.format(addr))
            self.gauge('http.ssl.days_left', days_left, tags=tags_list)

            service_checks.append((self.SC_SSL_CERT, status, msg))

        return service_checks

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        instance_name = self.normalize(instance['name'])
        url = instance.get('url', None)
        tags = instance.get('tags', [])
        tags.append("instance:{}".format(instance_name))

        # Only add the URL tag if it's not already present
        if not filter(re.compile('^url:').match, tags):
            tags.append('url:{}'.format(url))

        if sc_name == self.SC_STATUS:
            # format the HTTP response body into the event
            if isinstance(msg, tuple):
                code, reason, content = msg

                # truncate and html-escape content
                if len(content) > 200:
                    content = content[:197] + '...'

                msg = "{:d} {}\n\n{}" % (code, reason, content)
                msg = msg.rstrip()

        self.service_check(sc_name, NetworkCheck.STATUS_TO_SERVICE_CHECK[status], tags=tags, message=msg)

    def check_cert_expiration(self, instance, timeout, instance_ca_certs, check_hostname,
                              client_cert=None, client_key=None):
        warning_days = int(instance.get('days_warning', 14))
        critical_days = int(instance.get('days_critical', 7))
        url = instance.get('url')

        o = urlparse(url)
        host = o.hostname
        server_name = instance.get('ssl_server_name', o.hostname)

        port = o.port or 443

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(float(timeout))
            sock.connect((host, port))
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = check_hostname
            context.load_verify_locations(instance_ca_certs)

            if client_cert and client_key:
                context.load_cert_chain(client_cert, keyfile=client_key)

            ssl_sock = context.wrap_socket(sock, server_hostname=server_name)
            cert = ssl_sock.getpeercert()

        except ssl.CertificateError as e:
            self.log.debug("The hostname on the SSL certificate does not match the given host: {}".format(e))
            return (Status.CRITICAL, 0, str(e))
        except Exception as e:
            self.log.debug("Site is down, unable to connect to get cert expiration: {}".format(e))
            return (Status.DOWN, 0, str(e))

        exp_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        days_left = exp_date - datetime.utcnow()

        self.log.debug("Exp_date: {}".format(exp_date))
        self.log.debug("days_left: {}".format(days_left))

        if days_left.days < 0:
            return (Status.DOWN, days_left.days, "Expired by {} days".format(days_left.days))

        elif days_left.days < critical_days:
            return (Status.CRITICAL, days_left.days, "This cert TTL is critical: only {} days before it expires"
                    .format(days_left.days))

        elif days_left.days < warning_days:
            return (Status.WARNING, days_left.days, "This cert is almost expired, only {} days left"
                    .format(days_left.days))

        else:
            return (Status.UP, days_left.days, "Days left: {}".format(days_left.days))
