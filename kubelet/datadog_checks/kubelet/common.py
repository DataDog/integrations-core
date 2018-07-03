# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from tagger import get_tags

try:
    from containers import is_excluded
except ImportError:
    # Don't fail on < 6.2
    import logging
    log = logging.getLogger(__name__)
    log.info('Agent does not provide filtering logic, disabling container filtering')

    def is_excluded(name, image):
        return False

SOURCE_TYPE = 'kubelet'

CADVISOR_DEFAULT_PORT = 0


def tags_for_pod(pod_id, cardinality):
    """
    Queries the tagger for a given pod uid
    :return: string array, empty if pod not found
    """
    return get_tags('kubernetes_pod://%s' % pod_id, cardinality)


def tags_for_docker(cid, cardinality):
    """
    Queries the tagger for a given container id
    :return: string array, empty if container not found
    """
    return get_tags('docker://%s' % cid, cardinality)


def get_pod_by_uid(uid, podlist):
    """
    Searches for a pod uid in the podlist and returns the pod if found
    :param uid: pod uid
    :param podlist: podlist dict object
    :return: pod dict object if found, None if not found
    """
    for pod in podlist.get("items", []):
        try:
            if pod["metadata"]["uid"] == uid:
                return pod
        except KeyError:
            continue
    return None


def is_static_pending_pod(pod):
    """
    Return if the pod is a static pending pod
    See https://github.com/kubernetes/kubernetes/pull/57106
    :param pod: dict
    :return: bool
    """
    try:
        if pod["metadata"]["annotations"]["kubernetes.io/config.source"] == "api":
            return False

        pod_status = pod["status"]
        if pod_status["phase"] != "Pending":
            return False

        return "containerStatuses" not in pod_status
    except KeyError:
        return False


class ContainerFilter(object):
    """
    Queries the podlist and the agent6's filtering logic to determine whether to
    send metrics for a given container.
    Results and podlist are cached between calls to avoid the repeated python-go switching
    cost (filter called once per prometheus metric), hence the ContainerFilter object MUST
    be re-created at every check run.

    Containers that are part of a static pod are not filtered, as we cannot curently
    reliably determine their image name to pass to the filtering logic.
    """
    def __init__(self, podlist):
        self.containers = {}
        self.static_pod_uids = set()
        self.cache = {}

        pods = podlist.get('items') or []

        for pod in pods:
            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            if is_static_pending_pod(pod):
                self.static_pod_uids.add(pod.get("metadata", {}).get("uid"))

            for ctr in pod.get('status', {}).get('containerStatuses', []):
                cid = ctr.get('containerID')
                if not cid:
                    continue
                self.containers[cid] = ctr
                if "://" in cid:
                    # cAdvisor pushes cids without orchestrator scheme
                    # re-register without the scheme
                    short_cid = cid.split("://", 1)[-1]
                    self.containers[short_cid] = ctr

    def is_excluded(self, cid, pod_uid=None):
        """
        Queries the agent6 container filter interface. It retrieves container
        name + image from the podlist, so static pod filtering is not supported.

        Result is cached between calls to avoid the python-go switching cost for
        prometheus metrics (will be called once per metric)
        :param cid: container id
        :param pod_uid: pod UID for static pod detection
        :return: bool
        """
        if not cid:
            return True

        if cid in self.cache:
            return self.cache[cid]

        if pod_uid and pod_uid in self.static_pod_uids:
            self.cache[cid] = False
            return False

        if cid not in self.containers:
            # Filter out metrics not coming from a container (system slices)
            self.cache[cid] = True
            return True
        ctr = self.containers[cid]
        if not ("name" in ctr and "image" in ctr):
            # Filter out invalid containers
            self.cache[cid] = True
            return True

        excluded = is_excluded(ctr.get("name"), ctr.get("image"))
        self.cache[cid] = excluded
        return excluded


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

    def configure_scraper(self, scraper, endpoint):
        """
        Configures a PrometheusScaper object with query credentials
        :param scraper: valid PrometheusScaper object
        :param endpoint: url that will be scraped
        """
        scraper.ssl_ca_cert = self._ssl_verify
        scraper.ssl_cert = self._ssl_cert
        scraper.ssl_private_key = self._ssl_private_key
        scraper.extra_headers = self.headers(endpoint) or {}
