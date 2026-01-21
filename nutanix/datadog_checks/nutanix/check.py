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
        self.collect_audits_enabled = is_affirmative(self.instance.get("collect_audits", True))
        self.collect_alerts_enabled = is_affirmative(self.instance.get("collect_alerts", True))

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
        self.log.info("[PC:%s:%s] Starting check...", self.pc_ip, self.pc_port)

        # Reset all state for new collection run
        self.infrastructure_monitor.reset_state()

        if not self._check_health():
            self.log.warning("[PC:%s:%s] Health check failed, aborting", self.pc_ip, self.pc_port)
            return

        # init time window to sync all API calls to use the same [start_time, end_time] time window
        self.infrastructure_monitor.init_collection_time_window()
        start_time, end_time = self.infrastructure_monitor.collection_time_window

        # Calculate window duration for logging
        from datetime import datetime

        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        window_seconds = (end_dt - start_dt).total_seconds()

        self.log.info(
            "[PC:%s:%s] Collecting metrics for %ds time window (from %s to %s)",
            self.pc_ip,
            self.pc_port,
            int(window_seconds),
            start_time,
            end_time,
        )

        self.log.info("[PC:%s:%s] Collecting infrastructure metrics...", self.pc_ip, self.pc_port)
        self.infrastructure_monitor.collect_cluster_metrics()
        self.log.info(
            "[PC:%s:%s] Collected %d cluster metrics, %d host metrics, and %d VM metrics",
            self.pc_ip,
            self.pc_port,
            self.infrastructure_monitor.cluster_metrics_count,
            self.infrastructure_monitor.host_metrics_count,
            self.infrastructure_monitor.vm_metrics_count,
        )

        if self.collect_events_enabled:
            self.log.info("[PC:%s:%s] Collecting events...", self.pc_ip, self.pc_port)
            events_count = self.activity_monitor.collect_events()
            self.log.info("[PC:%s:%s] Collected %d events", self.pc_ip, self.pc_port, events_count)
        else:
            self.log.debug("[PC:%s:%s] Events collection disabled", self.pc_ip, self.pc_port)

        if self.collect_tasks_enabled:
            self.log.info("[PC:%s:%s] Collecting tasks...", self.pc_ip, self.pc_port)
            tasks_count = self.activity_monitor.collect_tasks()
            self.log.info("[PC:%s:%s] Collected %d tasks", self.pc_ip, self.pc_port, tasks_count)
        else:
            self.log.debug("[PC:%s:%s] Tasks collection disabled", self.pc_ip, self.pc_port)

        if self.collect_audits_enabled:
            self.log.info("[PC:%s:%s] Collecting audits...", self.pc_ip, self.pc_port)
            audits_count = self.activity_monitor.collect_audits()
            self.log.info("[PC:%s:%s] Collected %d audits", self.pc_ip, self.pc_port, audits_count)
        else:
            self.log.debug("[PC:%s:%s] Audits collection disabled", self.pc_ip, self.pc_port)

        if self.collect_alerts_enabled:
            self.log.info("[PC:%s:%s] Collecting alerts...", self.pc_ip, self.pc_port)
            alerts_count = self.activity_monitor.collect_alerts()
            self.log.info("[PC:%s:%s] Collected %d alerts", self.pc_ip, self.pc_port, alerts_count)
        else:
            self.log.debug("[PC:%s:%s] Alerts collection disabled", self.pc_ip, self.pc_port)

        if self.infrastructure_monitor.external_tags:
            self.log.info(
                "[PC:%s:%s] Applied %d external tags",
                self.pc_ip,
                self.pc_port,
                len(self.infrastructure_monitor.external_tags),
            )
            self.set_external_tags(self.infrastructure_monitor.external_tags)

        self.log.info("[PC:%s:%s] Check completed successfully", self.pc_ip, self.pc_port)

    def _check_health(self):
        try:
            response = self._make_request_with_retry(self.health_check_url, method='get')
            response.raise_for_status()
            self.gauge("health.up", 1, tags=self.base_tags)
            self.log.debug("[PC:%s:%s] Health check passed", self.pc_ip, self.pc_port)
            return True

        except (HTTPError, InvalidURL, ConnectionError, Timeout) as e:
            self.log.error("[PC:%s:%s] Failed to connect: %s", self.pc_ip, self.pc_port, str(e))
            self.gauge("health.up", 0, tags=self.base_tags)
            return False

        except Exception as e:
            self.log.exception("[PC:%s:%s] Unexpected connection error: %s", self.pc_ip, self.pc_port, e)
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
        self.log.debug(
            "[PC:%s:%s] HTTP request: %s %s, kwargs=%s", self.pc_ip, self.pc_port, method.upper(), url, kwargs
        )
        http_method = getattr(self.http, method.lower())
        response = http_method(url, **kwargs)
        status = response.status_code

        # rate limits
        if status == 429:
            self.log.debug(
                "[PC:%s:%s] HTTP 429 rate limited: %s %s, payload_length=%s",
                self.pc_ip,
                self.pc_port,
                method.upper(),
                url,
                len(response.content) if response.content else 0,
            )

        # other errors
        elif not response.ok:
            error_msg = "Unknown error"
            try:
                error_response = response.json()
                if error_data := error_response.get("data", {}):
                    errors = error_data.get("error", [])
                    if errors:
                        error_msg = str(errors)
            except Exception:
                error_msg = response.text or str(status)

            self.log.error(
                "[PC:%s:%s] HTTP non-2xx response: %s %s, status_code=%s, error=%s",
                self.pc_ip,
                self.pc_port,
                method.upper(),
                url,
                status,
                error_msg,
            )
        else:
            # Success - log at trace level with payload
            try:
                payload = response.json()
                self.log.trace(
                    "[PC:%s:%s] HTTP response: %s %s, status=%s, payload=%s",
                    self.pc_ip,
                    self.pc_port,
                    method.upper(),
                    url,
                    status,
                    payload,
                )
            except Exception:
                self.log.trace(
                    "[PC:%s:%s] HTTP response: %s %s, status=%s, content_length=%s",
                    self.pc_ip,
                    self.pc_port,
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
                break

            all_items.extend(data)

            # check next page
            links = payload.get("metadata", {}).get("links", [])
            next_link = next((l.get("href") for l in links if l.get("rel") == "next"), None)

            if not next_link:
                break

            page += 1
            req_params["$page"] = page

        self.log.debug(
            "[PC:%s:%s] Fetched %d items from %s (%d pages)",
            self.pc_ip,
            self.pc_port,
            len(all_items),
            endpoint,
            page + 1,
        )
        return all_items

    def _get_request_data(self, endpoint, params=None):
        """Make an API request to Prism Central and return the data field."""
        url = f"{self.base_url}/{endpoint}"
        response = self._make_request_with_retry(url, method='get', params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})
