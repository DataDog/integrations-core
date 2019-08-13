# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import re
import socket
import ssl
import time
from datetime import datetime

import _strptime  # noqa
import requests
from six import string_types
from six.moves.urllib.parse import urlparse

from datadog_checks.base import ensure_unicode, is_affirmative
from datadog_checks.base.checks import NetworkCheck, Status

from .adapters import WeakCiphersAdapter, WeakCiphersHTTPSConnection
from .config import DEFAULT_EXPECTED_CODE, from_instance
from .utils import get_ca_certs_path

DEFAULT_EXPIRE_DAYS_WARNING = 14
DEFAULT_EXPIRE_DAYS_CRITICAL = 7
DEFAULT_EXPIRE_WARNING = DEFAULT_EXPIRE_DAYS_WARNING * 24 * 3600
DEFAULT_EXPIRE_CRITICAL = DEFAULT_EXPIRE_DAYS_CRITICAL * 24 * 3600
CONTENT_LENGTH = 200

DATA_METHODS = ['POST', 'PUT', 'DELETE', 'PATCH']


class HTTPCheck(NetworkCheck):
    SOURCE_TYPE_NAME = 'system'
    SC_STATUS = 'http.can_connect'
    SC_SSL_CERT = 'http.ssl_cert'

    HTTP_CONFIG_REMAPPER = {
        'client_cert': {'name': 'tls_cert'},
        'client_key': {'name': 'tls_private_key'},
        'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': True},
        'ignore_ssl_warning': {'name': 'tls_ignore_warning'},
        'ca_certs': {'name': 'tls_ca_cert'},
    }

    def __init__(self, name, init_config, instances):
        super(HTTPCheck, self).__init__(name, init_config, instances)

        self.ca_certs = init_config.get('ca_certs')
        if not self.ca_certs:
            self.ca_certs = get_ca_certs_path()

        self.HTTP_CONFIG_REMAPPER['ca_certs']['default'] = self.ca_certs

        if is_affirmative(self.instance.get('disable_ssl_validation', True)):
            self.http.options['verify'] = False

    def _check(self, instance):
        (
            addr,
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
            weakcipher,
            check_hostname,
            allow_redirects,
            stream,
        ) = from_instance(instance, self.ca_certs)
        timeout = self.http.options['timeout'][0]
        start = time.time()
        self.http.options['headers'] = headers

        def send_status_up(logMsg):
            # TODO: A6 log needs bytes and cannot handle unicode
            self.log.debug(logMsg)
            service_checks.append((self.SC_STATUS, Status.UP, "UP"))

        def send_status_down(loginfo, down_msg):
            # TODO: A6 log needs bytes and cannot handle unicode
            self.log.info(loginfo)
            if include_content:
                down_msg += '\nContent: {}'.format(content[:CONTENT_LENGTH])
            service_checks.append((self.SC_STATUS, Status.DOWN, down_msg))

        # Store tags in a temporary list so that we don't modify the global tags data structure
        tags_list = list(tags)
        tags_list.append('url:{}'.format(addr))
        instance_name = self.normalize(instance['name'])
        tags_list.append("instance:{}".format(instance_name))
        service_checks = []
        r = None
        try:
            parsed_uri = urlparse(addr)
            self.log.debug("Connecting to {}".format(addr))
            self.http.session.trust_env = False
            if weakcipher:
                base_addr = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
                self.http.session.mount(base_addr, WeakCiphersAdapter())
                self.log.debug(
                    "Weak Ciphers will be used for {}. Supported Cipherlist: {}".format(
                        base_addr, WeakCiphersHTTPSConnection.SUPPORTED_CIPHERS
                    )
                )

            # Add 'Content-Type' for non GET requests when they have not been specified in custom headers
            if method.upper() in DATA_METHODS and not headers.get('Content-Type'):
                self.http.options['headers']['Content-Type'] = 'application/x-www-form-urlencoded'

            r = getattr(self.http, method.lower())(
                addr,
                persist=True,
                allow_redirects=allow_redirects,
                stream=stream,
                json=data if method.upper() in DATA_METHODS and isinstance(data, dict) else None,
                data=data if method.upper() in DATA_METHODS and isinstance(data, string_types) else None,
            )
        except (socket.timeout, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            length = int((time.time() - start) * 1000)
            self.log.info("{} is DOWN, error: {}. Connection failed after {} ms".format(addr, str(e), length))
            service_checks.append(
                (self.SC_STATUS, Status.DOWN, "{}. Connection failed after {} ms".format(str(e), length))
            )

        except socket.error as e:
            length = int((time.time() - start) * 1000)
            self.log.info("{} is DOWN, error: {}. Connection failed after {} ms".format(addr, repr(e), length))
            service_checks.append(
                (self.SC_STATUS, Status.DOWN, "Socket error: {}. Connection failed after {} ms".format(repr(e), length))
            )

        except Exception as e:
            length = int((time.time() - start) * 1000)
            self.log.error("Unhandled exception {}. Connection failed after {} ms".format(str(e), length))
            raise

        else:
            # Only add the URL tag if it's not already present
            if not any(filter(re.compile('^url:').match, tags_list)):
                tags_list.append('url:{}'.format(addr))

            # Only report this metric if the site is not down
            if response_time and not service_checks:
                # Stop the timer as early as possible
                running_time = time.time() - start
                self.gauge('network.http.response_time', running_time, tags=tags_list)

            content = r.text

            # Check HTTP response status code
            if not (service_checks or re.match(http_response_status_code, str(r.status_code))):
                if http_response_status_code == DEFAULT_EXPECTED_CODE:
                    expected_code = "1xx or 2xx or 3xx"
                else:
                    expected_code = http_response_status_code

                message = "Incorrect HTTP return code for url {}. Expected {}, got {}.".format(
                    addr, expected_code, str(r.status_code)
                )

                if include_content:
                    message += '\nContent: {}'.format(content[:CONTENT_LENGTH])

                self.log.info(message)

                service_checks.append((self.SC_STATUS, Status.DOWN, message))

            if not service_checks:
                # Host is UP
                # Check content matching is set
                if content_match:
                    if re.search(content_match, content, re.UNICODE):
                        if reverse_content_match:
                            send_status_down(
                                '{} is found in return content with the reverse_content_match option'.format(
                                    ensure_unicode(content_match)
                                ),
                                'Content "{}" found in response with the reverse_content_match'.format(
                                    ensure_unicode(content_match)
                                ),
                            )
                        else:
                            send_status_up("{} is found in return content".format(ensure_unicode(content_match)))

                    else:
                        if reverse_content_match:
                            send_status_up(
                                "{} is not found in return content with the reverse_content_match option".format(
                                    ensure_unicode(content_match)
                                )
                            )
                        else:
                            send_status_down(
                                "{} is not found in return content".format(ensure_unicode(content_match)),
                                'Content "{}" not found in response.'.format(ensure_unicode(content_match)),
                            )

                else:
                    send_status_up("{} is UP".format(addr))
        finally:
            if r is not None:
                r.close()
            # resets the wrapper Session object
            self.http._session = None

        # Report status metrics as well
        if service_checks:
            can_status = 1 if service_checks[0][1] == "UP" else 0
            self.gauge('network.http.can_connect', can_status, tags=tags_list)

            # cant_connect is useful for top lists
            cant_status = 0 if service_checks[0][1] == "UP" else 1
            self.gauge('network.http.cant_connect', cant_status, tags=tags_list)

        if ssl_expire and parsed_uri.scheme == "https":
            status, days_left, seconds_left, msg = self.check_cert_expiration(
                instance, timeout, instance_ca_certs, check_hostname, client_cert, client_key
            )
            tags_list = list(tags)
            tags_list.append('url:{}'.format(addr))
            tags_list.append("instance:{}".format(instance_name))
            self.gauge('http.ssl.days_left', days_left, tags=tags_list)
            self.gauge('http.ssl.seconds_left', seconds_left, tags=tags_list)

            service_checks.append((self.SC_SSL_CERT, status, msg))

        return service_checks

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        instance_name = self.normalize(instance['name'])
        url = instance.get('url', None)
        if url is not None:
            url = ensure_unicode(url)
        tags = instance.get('tags', [])
        tags.append("instance:{}".format(instance_name))

        # Only add the URL tag if it's not already present
        if not any(filter(re.compile('^url:').match, tags)):
            tags.append('url:{}'.format(url))

        if sc_name == self.SC_STATUS:
            # format the HTTP response body into the event
            if isinstance(msg, tuple):
                code, reason, content = msg

                # truncate and html-escape content
                if len(content) > 200:
                    content = content[:197] + '...'

                msg = '{} {}\n\n{}'.format(code, reason, content)
                msg = msg.rstrip()

        self.service_check(sc_name, NetworkCheck.STATUS_TO_SERVICE_CHECK[status], tags=tags, message=msg)

    def check_cert_expiration(
        self, instance, timeout, instance_ca_certs, check_hostname, client_cert=None, client_key=None
    ):
        # thresholds expressed in seconds take precedence over those expressed in days
        seconds_warning = (
            int(instance.get('seconds_warning', 0))
            or int(instance.get('days_warning', 0)) * 24 * 3600
            or DEFAULT_EXPIRE_WARNING
        )
        seconds_critical = (
            int(instance.get('seconds_critical', 0))
            or int(instance.get('days_critical', 0)) * 24 * 3600
            or DEFAULT_EXPIRE_CRITICAL
        )
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

        except Exception as e:
            msg = str(e)
            if 'expiration' in msg:
                self.log.debug("error: {}. Cert might be expired.".format(e))
                return Status.DOWN, 0, 0, msg
            elif 'Hostname mismatch' in msg or "doesn't match" in msg:
                self.log.debug("The hostname on the SSL certificate does not match the given host: {}".format(e))
                return Status.CRITICAL, 0, 0, msg
            else:
                self.log.debug("Site is down, unable to connect to get cert expiration: {}".format(e))
                return Status.DOWN, 0, 0, msg

        exp_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        time_left = exp_date - datetime.utcnow()
        days_left = time_left.days
        seconds_left = time_left.total_seconds()

        self.log.debug("Exp_date: {}".format(exp_date))
        self.log.debug("seconds_left: {}".format(seconds_left))

        if seconds_left < seconds_critical:
            return (
                Status.CRITICAL,
                days_left,
                seconds_left,
                "This cert TTL is critical: only {} days before it expires".format(days_left),
            )

        elif seconds_left < seconds_warning:
            return (
                Status.WARNING,
                days_left,
                seconds_left,
                "This cert is almost expired, only {} days left".format(days_left),
            )

        else:
            return Status.UP, days_left, seconds_left, "Days left: {}".format(days_left)
