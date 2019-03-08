import socket
import ssl
import requests
from datetime import datetime
from datadog_checks.checks import AgentCheck
from cryptography import x509
from cryptography.hazmat.backends import default_backend

DEFAULT_EXPIRE_DAYS_WARNING = 14
DEFAULT_EXPIRE_DAYS_CRITICAL = 7
DEFAULT_EXPIRE_WARNING = DEFAULT_EXPIRE_DAYS_WARNING * 24 * 3600
DEFAULT_EXPIRE_CRITICAL = DEFAULT_EXPIRE_DAYS_CRITICAL * 24 * 3600


def main():
    # get and check config
    hostname = 'google.com'
    # hostname = ''
    ip = '1.1.1.1'
    port = '443'
    local_cert_path = 'mock.cert'

    # config must include local or remote endpoint for checking SSL cert
    # check if path/URL is valid

    # try to connect/read local file
    # if can't can_connect critical, otherwise up
    if len(hostname) > 1:
        print("getting remote")
        cert_data = check_remote_cert(hostname, port)
    elif len(local_cert_path) > 1:
        print("getting local")
        cert_data = check_local_cert(local_cert_path)
    else:
        print("Hostname or local path to certificate are required config options.")

    # TLS/SSL protocol only applies to remote certs, maybe not useful?
    # https://www.sslsupportdesk.com/clearing-confusion-tls-ssl-certificates-are-the-same-thing/
    check_protocol_version(hostname, port)

    # read cert, check is_valid
    # some exceptions we can use: https://cryptography.io/en/latest/x509/reference/#cryptography.x509.InvalidVersion
    # will probably need to make some invalid certs: https://cryptography.io/en/latest/x509/reference/#x-509-certificate-builder

    # remote_cert = x509.load_der_x509_certificate(peer_cert, default_backend())
    # print(cert_data.version)
    # print(peer_cert['notAfter'])
    # print(remote_cert.not_valid_after)

    # calculate expiration, send metrics, tags
    check_expiration(cert_data.not_valid_after)


def check_expiration(exp_date):
    # add variables for custom configured thresholds
    seconds_warning = \
        DEFAULT_EXPIRE_WARNING
    seconds_critical = \
        DEFAULT_EXPIRE_CRITICAL
    time_left = exp_date - datetime.utcnow()
    days_left = time_left.days
    seconds_left = time_left.total_seconds()
    print("Exp_date: {}".format(exp_date))
    if seconds_left < seconds_critical:
        print('critical', days_left, seconds_left,
              "This cert TTL is critical: only {} days before it expires".format(days_left))
    elif seconds_left < seconds_warning:
        print('warning', days_left, seconds_left,
              "This cert is almost expired, only {} days left".format(days_left))
    else:
        print('up', days_left, seconds_left, "Days left: {}".format(days_left))


def can_connect(status, message=''):
    print("can_connect: {}, {}".format(status, message))


def is_valid(status, message=''):
    print("is_valid: {}, {}".format(status, message))


def is_expiring(status, message=''):
    print("is_expiring: {}, {}".format(status, message))


def check_protocol_version(hostname, port):
    context = ssl.create_default_context()
    sock = socket.create_connection((hostname, port))
    ssock = context.wrap_socket(sock, server_hostname=hostname)
    print(ssock.version())


def check_remote_cert(hostname, port):
    try:
        context = ssl.create_default_context()
        sock = socket.create_connection((hostname, port))
        ssock = context.wrap_socket(sock, server_hostname=hostname)
        return x509.load_der_x509_certificate(ssock.getpeercert(binary_form=True), default_backend())
    except Exception as e:
        can_connect('critical', e)


def check_local_cert(local_cert_path):
    try:
        local_cert_file = open(local_cert_path, 'rb')
        local_cert_data = x509.load_pem_x509_certificate(local_cert_file.read(), default_backend())
        can_connect('up')
        return local_cert_data
    except Exception as e:
        can_connect('critical', e)
        # self.service_check('my_check.all_good', self.CRITICAL, e)


main()
