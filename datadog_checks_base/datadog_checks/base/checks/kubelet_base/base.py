# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta

from ...utils.date import UTC, parse_rfc3339
from .. import AgentCheck

try:
    from datadog_agent import get_config
except ImportError:

    def get_config(key):
        return ""


class KubeletBase(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(KubeletBase, self).__init__(name, init_config, instances)

    def perform_kubelet_query(self, url, verbose=True, stream=False):
        """
        Perform and return a GET request against kubelet. Support auth and TLS validation.
        """

        # If tls_verify is False, then suppress tls warning
        if self.kubelet_credentials.verify() is False:
            self.http.ignore_tls_warning = True

        return self.http.get(
            url,
            verify=self.kubelet_credentials.verify(),
            cert=self.kubelet_credentials.cert_pair(),
            headers=self.kubelet_credentials.headers(url),
            params={'verbose': verbose},
            stream=stream,
        )

    def retrieve_pod_list(self):
        try:
            cutoff_date = self.compute_pod_expiration_datetime()
            with self.perform_kubelet_query(self.pod_list_url, stream=True) as r:
                if cutoff_date:
                    f = ExpiredPodFilter(cutoff_date)
                    pod_list = json.load(r.raw, object_hook=f.json_hook)
                    pod_list['expired_count'] = f.expired_count
                    if pod_list.get('items') is not None:
                        # Filter out None items from the list
                        pod_list['items'] = [p for p in pod_list['items'] if p is not None]
                else:
                    pod_list = json.load(r.raw)

            if pod_list.get('items') is None:
                # Sanitize input: if no pods are running, 'items' is a NoneObject
                pod_list['items'] = []
            return pod_list
        except Exception as e:
            self.log.warning("failed to retrieve pod list from the kubelet at %s : %s", self.pod_list_url, e)
            return {}

    @staticmethod
    def compute_pod_expiration_datetime():
        """
        Looks up the agent's kubernetes_pod_expiration_duration option and returns either:
          - None if expiration is disabled (set to 0)
          - A (timezone aware) datetime object to compare against
        """
        try:
            seconds = int(get_config("kubernetes_pod_expiration_duration"))
            if seconds == 0:  # Expiration disabled
                return None
            return datetime.utcnow().replace(tzinfo=UTC) - timedelta(seconds=seconds)
        except (ValueError, TypeError):
            return None


class ExpiredPodFilter(object):
    """
    Allows to filter old pods out of the podlist by providing a decoding hook
    """

    def __init__(self, cutoff_date):
        self.expired_count = 0
        self.cutoff_date = cutoff_date

    def json_hook(self, obj):
        # Not a pod (hook is called for all objects)
        if 'metadata' not in obj or 'status' not in obj:
            return obj

        # Quick exit for running/pending containers
        pod_phase = obj.get('status', {}).get('phase')
        if pod_phase in ["Running", "Pending"]:
            return obj

        # Filter out expired terminated pods, based on container finishedAt time
        expired = True
        for ctr in obj['status'].get('containerStatuses', []):
            if "terminated" not in ctr.get("state", {}):
                expired = False
                break
            finishedTime = ctr["state"]["terminated"].get("finishedAt")
            if not finishedTime:
                expired = False
                break
            if parse_rfc3339(finishedTime) > self.cutoff_date:
                expired = False
                break
        if not expired:
            return obj

        # We are ignoring this pod
        self.expired_count += 1
        return None


class KubeletCredentials(object):
    """
    Holds the configured credentials to connect to the Kubelet.
    """

    def __init__(self, kubelet_conn_info):
        """
        Parses the kubelet_conn_info dict and computes credentials
        :param kubelet_conn_info: dict from kubeutil.get_connection_info()
        """
        self._token = None
        self._ssl_verify = None
        self._ssl_cert = None
        self._ssl_private_key = None

        if kubelet_conn_info.get('verify_tls') == 'false':
            self._ssl_verify = False
        else:
            self._ssl_verify = kubelet_conn_info.get('ca_cert')

        cert = kubelet_conn_info.get('client_crt')
        key = kubelet_conn_info.get('client_key')
        if cert and key:
            self._ssl_cert = cert
            self._ssl_private_key = key
            return  # Don't import the token if we have valid certs

        if 'token' in kubelet_conn_info:
            self._token = kubelet_conn_info['token']

    def cert_pair(self):
        """
        Returns the client certificates
        :return: tuple (crt,key) or None
        """
        if self._ssl_cert and self._ssl_private_key:
            return (self._ssl_cert, self._ssl_private_key)
        else:
            return None

    def headers(self, url):
        """
        Returns the https headers with credentials, if token is used and url is https
        :param url: url to be queried, including scheme
        :return: dict or None
        """
        if self._token and url.lower().startswith('https'):
            return {'Authorization': 'Bearer {}'.format(self._token)}
        else:
            return None

    def verify(self):
        """
        Returns the SSL verification parameters
        :return: CA cert path, None or False (SSL verification explicitly disabled)
        """
        return self._ssl_verify

    def configure_scraper(self, scraper_config):
        """
        Configures a PrometheusScaper object with query credentials
        :param scraper: valid PrometheusScaper object
        :param endpoint: url that will be scraped
        """
        endpoint = scraper_config['prometheus_url']
        scraper_config.update(
            {
                'ssl_ca_cert': self._ssl_verify,
                'ssl_cert': self._ssl_cert,
                'ssl_private_key': self._ssl_private_key,
                'extra_headers': self.headers(endpoint) or {},
            }
        )


def urljoin(*args):
    """
    Joins given arguments into an url. Trailing but not leading slashes are
    stripped for each argument.
    :return: string
    """
    return '/'.join(arg.strip('/') for arg in args)
