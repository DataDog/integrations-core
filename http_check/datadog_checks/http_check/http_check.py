# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

from datetime import datetime
import _strptime # noqa
import re
import socket
import ssl
import time
import warnings
from urlparse import urlparse

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests_ntlm import HttpNtlmAuth
from datadog_checks.checks import NetworkCheck, Status

from .adapters import WeakCiphersAdapter, WeakCiphersHTTPSConnection
from .utils import get_ca_certs_path
from .config import from_instance, DEFAULT_EXPECTED_CODE


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

    def __init__(self, name, init_config, agentConfig, instances=None):
        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

        self.ca_certs = init_config.get('ca_certs')
        if not self.ca_certs:
            self.ca_certs = get_ca_certs_path()

    def _check(self, instance):
        addr, ntlm_domain, username, password, client_cert, client_key, method, data, http_response_status_code, \
            timeout, include_content, headers, response_time, content_match, reverse_content_match, tags, \
            disable_ssl_validation, ssl_expire, instance_ca_certs, weakcipher, check_hostname, ignore_ssl_warning, \
            skip_proxy, allow_redirects = from_instance(instance, self.ca_certs)

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
            status, days_left, seconds_left, msg = self.check_cert_expiration(instance, timeout, instance_ca_certs,
                                                                              check_hostname, client_cert, client_key)
            tags_list = list(tags)
            tags_list.append('url:{}'.format(addr))
            self.gauge('http.ssl.days_left', days_left, tags=tags_list)
            self.gauge('http.ssl.seconds_left', seconds_left, tags=tags_list)

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
        # thresholds expressed in seconds take precendence over those expressed in days
        seconds_warning = \
            int(instance.get('seconds_warning', 0)) or \
            int(instance.get('days_warning', 0)) * 24 * 3600 or \
            DEFAULT_EXPIRE_WARNING
        seconds_critical = \
            int(instance.get('seconds_critical', 0)) or \
            int(instance.get('days_critical', 0)) * 24 * 3600 or \
            DEFAULT_EXPIRE_CRITICAL
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
            return (Status.CRITICAL, 0, 0, str(e))
        except Exception as e:
            self.log.debug("Site is down, unable to connect to get cert expiration: {}".format(e))
            return (Status.DOWN, 0, 0, str(e))

        exp_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        time_left = exp_date - datetime.utcnow()
        days_left = time_left.days
        seconds_left = time_left.total_seconds()

        self.log.debug("Exp_date: {}".format(exp_date))
        self.log.debug("seconds_left: {}".format(seconds_left))

        if seconds_left < 0:
            return (Status.DOWN, days_left, seconds_left, "Expired by {} days".format(days_left))

        elif seconds_left < seconds_critical:
            return (Status.CRITICAL, days_left, seconds_left,
                    "This cert TTL is critical: only {} days before it expires".format(days_left))

        elif seconds_left < seconds_warning:
            return (Status.WARNING, days_left, seconds_left,
                    "This cert is almost expired, only {} days left".format(days_left))

        else:
            return (Status.UP, days_left, seconds_left, "Days left: {}".format(days_left))
