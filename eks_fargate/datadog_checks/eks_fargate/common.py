# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.date import parse_rfc3339


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
    Holds the configured credentials to connect to the Kubelet (via APIServer in the case of EKS Fargate).
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
