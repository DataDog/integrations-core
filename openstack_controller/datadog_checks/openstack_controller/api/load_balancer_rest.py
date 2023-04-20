# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

def filter_keys(map, keys_to_filter):
    return {k: map[k] for k in keys_to_filter}

class LoadBalancerRest:
    def __init__(self, log, http, endpoint):
        self.log = log
        self.http = http
        self.endpoint = endpoint

    def get_response_time(self):
        response = self.http.get('{}'.format(self.endpoint))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.elapsed.total_seconds() * 1000

    def get_loadbalancers(self):
        url = f"{self.endpoint}/v2/lbaas/loadbalancers"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())

        metrics_list = [
            "id",
            "name",
            "provisioning_status",
            "operating_status",
            "listeners",
            "pools",
            "admin_state_up",
        ]
        loadbalancers_metrics = {}
        for loadbalancer in response.json()['loadbalancers']:
            loadbalancers_metrics[loadbalancer["id"]] = filter_keys(loadbalancer, metrics_list)

        return loadbalancers_metrics

    def get_listeners(self):
        url = f"{self.endpoint}/v2/lbaas/listeners"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['listeners']

    def get_pools(self):
        url = f"{self.endpoint}/v2/lbaas/pools"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['pools']

    def get_members_by_pool(self, pool_id):
        url = f"{self.endpoint}/v2/lbaas/pools/{pool_id}/members"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['members']

    def get_healthmonitors(self):
        url = f"{self.endpoint}/v2/lbaas/healthmonitors"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['healthmonitors']

    def get_loadbalancer_statistics(self, loadbalancer_id):
        url = f"{self.endpoint}/v2/lbaas/loadbalancers/{loadbalancer_id}/stats"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['stats']

    def get_listener_statistics(self, listener_id):
        url = f"{self.endpoint}/v2/lbaas/listeners/{listener_id}/stats"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['stats']

    def get_listeners_by_loadbalancer(self, loadbalancer_id):
        listeners = self.get_listeners()
        result = [l for l in listeners if loadbalancer_id in [lb.get("id") for lb in l.get("loadbalancers")]]
        return result

    def get_pools_by_loadbalancer(self, loadbalancer_id):
        pools = self.get_pools()
        result = [p for p in pools if loadbalancer_id in [lb.get("id") for lb in p.get("loadbalancers")]]
        return result

    def get_healthmonitors_by_pool(self, pool_id):
        healthmonitors = self.get_healthmonitors()
        result = [hm for hm in healthmonitors if pool_id in [pool.get("id") for pool in hm.get("pools")]]
        return result

    def get_amphorae(self):
        url = f"{self.endpoint}/v2/octavia/amphorae"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['amphorae']

    def get_amphorae_by_loadbalancer(self, loadbalancer_id):
        amphorae = self.get_amphorae()
        result = [a for a in amphorae if a.get("load_balancer_id") == loadbalancer_id]
        return result

    def get_amphora_statistics(self, amphora_id):
        url = f"{self.endpoint}/v2/octavia/amphorae/{amphora_id}/stats"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['amphora_stats']
