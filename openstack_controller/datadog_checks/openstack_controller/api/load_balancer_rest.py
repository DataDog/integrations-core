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
        keys_list = [
            "id",
            "name",
            "provisioning_status",
            "operating_status",
            "listeners",
            "pools",
            "admin_state_up",
        ]
        loadbalancers_keys = {}
        for loadbalancer in response.json()['loadbalancers']:
            loadbalancers_keys[loadbalancer["id"]] = filter_keys(loadbalancer, keys_list)
        return loadbalancers_keys

    def get_loadbalancer_statistics(self, loadbalancer_id):
        url = f"{self.endpoint}/v2/lbaas/loadbalancers/{loadbalancer_id}/stats"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['stats']

    def get_listeners(self):
        url = f"{self.endpoint}/v2/lbaas/listeners"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        keys_list = [
            "id",
            "name",
            "loadbalancers",
            "connection_limit",
            "timeout_client_data",
            "timeout_member_connect",
            "timeout_member_data",
            "timeout_tcp_inspect",
        ]
        listeners_keys = {}
        for listener in response.json()['listeners']:
            listeners_keys[listener["id"]] = filter_keys(listener, keys_list)
        return listeners_keys

    def get_listener_statistics(self, listener_id):
        url = f"{self.endpoint}/v2/lbaas/listeners/{listener_id}/stats"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        return response.json()['stats']

    def get_listeners_by_loadbalancer(self, loadbalancer_id):
        listeners = self.get_listeners()
        result = {
            id: l for id, l in listeners.items() if loadbalancer_id in [lb.get("id") for lb in l.get("loadbalancers")]
        }
        self.log.debug("response: %s", result)
        return result

    def get_pools(self):
        url = f"{self.endpoint}/v2/lbaas/pools"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        keys_list = [
            "id",
            "name",
            "provisioning_status",
            "operating_status",
            "listeners",
            "loadbalancers",
            "members",
            "healthmonitor_id",
            "admin_state_up",
        ]
        pools_keys = {}
        for pool in response.json()['pools']:
            pools_keys[pool["id"]] = filter_keys(pool, keys_list)
        return pools_keys

    def get_pools_by_loadbalancer(self, loadbalancer_id):
        pools = self.get_pools()
        result = {
            id: p for id, p in pools.items() if loadbalancer_id in [lb.get("id") for lb in p.get("loadbalancers")]
        }
        return result

    def get_members_by_pool(self, pool_id):
        url = f"{self.endpoint}/v2/lbaas/pools/{pool_id}/members"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        keys_list = [
            "id",
            "name",
            "provisioning_status",
            "operating_status",
            "admin_state_up",
            "weight",
        ]
        members_keys = {}
        for member in response.json()['members']:
            members_keys[member["id"]] = filter_keys(member, keys_list)
        return members_keys

    def get_healthmonitors(self):
        url = f"{self.endpoint}/v2/lbaas/healthmonitors"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        keys_list = [
            "id",
            "name",
            "provisioning_status",
            "operating_status",
            "type",
            "admin_state_up",
            "delay",
            "max_retries",
            "pools",
            "max_retries_down",
            "timeout",
        ]
        healthmonitors_keys = {}
        for healthmonitor in response.json()['healthmonitors']:
            healthmonitors_keys[healthmonitor["id"]] = filter_keys(healthmonitor, keys_list)
        return healthmonitors_keys

    def get_healthmonitors_by_pool(self, pool_id):
        healthmonitors = self.get_healthmonitors()
        result = {
            id: hm for id, hm in healthmonitors.items() if pool_id in [pool.get("id") for pool in hm.get("pools")]
        }
        return result

    def get_amphorae(self):
        url = f"{self.endpoint}/v2/octavia/amphorae"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        keys_list = [
            "id",
            "compute_id",
            "status",
            "loadbalancer_id",
        ]
        amphorae_keys = {}
        for amphora in response.json()['amphorae']:
            amphorae_keys[amphora["id"]] = filter_keys(amphora, keys_list)
        return amphorae_keys

    def get_amphorae_by_loadbalancer(self, loadbalancer_id):
        amphorae = self.get_amphorae()
        result = {id: a for id, a in amphorae.items() if a.get("loadbalancer_id") == loadbalancer_id}
        return result

    def get_amphora_statistics(self, amphora_id):
        url = f"{self.endpoint}/v2/octavia/amphorae/{amphora_id}/stats"
        response = self.http.get(url)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        keys_list = [
            "active_connections",
            "bytes_in",
            "bytes_out",
            "id",
            "listener_id",
            "loadbalancer_id",
            "request_errors",
            "total_connections",
        ]
        amphorae_stats_keys = {}
        for stats in response.json()['amphora_stats']:
            amphorae_stats_keys[stats["id"]] = filter_keys(stats, keys_list)
        return amphorae_stats_keys
