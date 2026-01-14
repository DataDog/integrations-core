# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.nutanix.activity_monitor import ActivityMonitor
from datadog_checks.nutanix.infrastructure_monitor import InfrastructureMonitor
from datadog_checks.nutanix.utils import retry_on_rate_limit


class NutanixCheck(AgentCheck):
    __NAMESPACE__ = 'nutanix'

    def __init__(self, name, init_config, instances):
        super(NutanixCheck, self).__init__(name, init_config, instances)

        self._parse_config()
        self._initialize_check_attributes()

    def _parse_config(self):
        self.sampling_interval = self.instance.get("min_collection_interval", 120)
        self.page_limit = self.instance.get("page_limit", 50)

        # setup
        self.pc_ip = self.instance.get("pc_ip")
        self.pc_port = self.instance.get("pc_port")
        if self.pc_ip and ":" in self.pc_ip:
            host, _, port = self.pc_ip.rpartition(":")
            if port.isdigit():
                if "pc_port" in self.instance:
                    raise ConfigurationError(f"Conflicting configuration: pc_ip ({port}) and pc_port ({self.pc_port})")
                self.pc_ip, self.pc_port = host, int(port)
        self.pc_port = self.pc_port or 9440

        # http auth
        pc_username = self.instance.get("pc_username")
        pc_password = self.instance.get("pc_password")

        if pc_username and "username" not in self.instance:
            self.instance["username"] = pc_username
        if pc_password and "password" not in self.instance:
            self.instance["password"] = pc_password

        self.collect_events_enabled = is_affirmative(self.instance.get("collect_events", True))
        self.collect_tasks_enabled = is_affirmative(self.instance.get("collect_tasks", True))

    def _initialize_check_attributes(self):
        self.base_url = f"{self.pc_ip}:{self.pc_port}"
        if not self.base_url.startswith("http"):
            self.base_url = "https://" + self.base_url

        self.health_check_url = f"{self.base_url}/console"

        self.base_tags = self.instance.get("tags", [])
        self.base_tags.append(f"prism_central:{self.pc_ip}")

        self.infrastructure_monitor = InfrastructureMonitor(self)
        self.activity_monitor = ActivityMonitor(self)

    @property
    def cluster_names(self):
        return self.infrastructure_monitor.cluster_names

    def check(self, _):
        # clear caches
        self.infrastructure_monitor.cluster_names = {}
        self.infrastructure_monitor.host_names = {}
        self.infrastructure_monitor.external_tags = []

        if not self._check_health():
            return

        self.infrastructure_monitor.collect_cluster_metrics()
        self.infrastructure_monitor.collect_vm_metrics()

        if self.collect_events_enabled:
            self.activity_monitor.collect_events()

        if self.collect_tasks_enabled:
            self.activity_monitor.collect_tasks()

        if self.infrastructure_monitor.external_tags:
            self.set_external_tags(self.infrastructure_monitor.external_tags)

    def _check_health(self):
        try:
            response = self._make_request_with_retry(self.health_check_url, method='get')
            response.raise_for_status()
            self.gauge("health.up", 1, tags=self.base_tags)
            self.log.debug("Health check passed for Prism Central at %s:%s", self.pc_ip, self.pc_port)
            return True

        except (HTTPError, InvalidURL, ConnectionError, Timeout) as e:
            self.log.error("Cannot connect to Prism Central at %s:%s : %s", self.pc_ip, self.pc_port, str(e))
            self.gauge("health.up", 0, tags=self.base_tags)
            return False

        except Exception as e:
            self.log.exception("Unexpected error when connecting to Prism Central: %s", e)
            self.gauge("health.up", 0, tags=self.base_tags)
            return False

    @retry_on_rate_limit
    def _make_request_with_retry(self, url, method='get', **kwargs):
        """Make an HTTP request with retry logic for rate limiting.

        Args:
            url: The URL to make the request to
            method: The HTTP method to use (get, post, put, delete, etc.)
            **kwargs: Additional arguments to pass to the request method (params, json, data, etc.)

        Returns:
            The response object from the request
        """
        self.log.debug("HTTP request: %s %s, kwargs=%s", method.upper(), url, kwargs)
        http_method = getattr(self.http, method.lower())
        response = http_method(url, **kwargs)
        status = response.status_code

        # rate limits
        if status == 429:
            self.log.debug(
                "HTTP 429 rate limited: %s %s, payload_length=%s",
                method.upper(),
                url,
                len(response.content) if response.content else 0,
            )

        # other errors
        elif not response.ok:
            self.log.debug(
                "HTTP non-2xx response: %s %s, status_code=%s, payload_length=%s",
                method.upper(),
                url,
                status,
                len(response.content) if response.content else 0,
            )

        return response

    def _get_paginated_request_data(self, endpoint, params=None):
        """Make a paginated API request to Prism Central and return the aggregated data field from all the pages."""

        all_items = []

        url = f"{self.base_url}/{endpoint}"

        # init pagination
        page = 0
        limit = self.page_limit

        # copy params
        req_params = {} if params is None else params.copy()

        req_params["$page"] = page
        req_params["$limit"] = limit

        while True:
            response = self._make_request_with_retry(url, method='get', params=req_params)
            response.raise_for_status()
            payload = response.json()

            data = payload.get("data", [])
            if not data:
                self.log.debug("Stopping pagination for %s: no data returned on page %d", endpoint, page)
                break

            all_items.extend(data)

            # check next page
            links = payload.get("metadata", {}).get("links", [])
            next_link = next((l.get("href") for l in links if l.get("rel") == "next"), None)

            if not next_link:
                break

            page += 1
            req_params["$page"] = page

        self.log.debug("Fetched %d items from %s (%d pages)", len(all_items), endpoint, page + 1)
        return all_items

    def _get_request_data(self, endpoint, params=None):
        """Make an API request to Prism Central and return the data field."""
        url = f"{self.base_url}/{endpoint}"
        response = self._make_request_with_retry(url, method='get', params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})
