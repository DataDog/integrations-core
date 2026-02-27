# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.control_m.client import ControlMClient
from datadog_checks.control_m.config_models import ConfigMixin
from datadog_checks.control_m.metrics import UP_STATES, JobCollector

_SERVICE_CHECK_CAN_LOGIN = "can_login"
_SERVICE_CHECK_CAN_CONNECT = "can_connect"


class ControlMCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = "control_m"

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        super().__init__(name, init_config, instances)

        self._client = ControlMClient(self)
        self._base_tags = [f"control_m_instance:{self._client.api_endpoint}"]
        self._job_collector = JobCollector(self, self._client, self._base_tags)

    def check(self, _: Any) -> None:
        auth_tags = self._auth_tags()

        if self._client.use_session_login:
            try:
                self._client.ensure_token()
            except Exception as e:
                self.service_check(
                    _SERVICE_CHECK_CAN_LOGIN,
                    self.CRITICAL,
                    tags=auth_tags,
                    message=f"Failed to authenticate to Control-M API: {e}",
                )
                self.service_check(
                    _SERVICE_CHECK_CAN_CONNECT,
                    self.CRITICAL,
                    tags=auth_tags,
                    message=f"Failed to authenticate to Control-M API: {e}",
                )
                self.gauge("can_login", 0, tags=auth_tags)
                self.gauge("can_connect", 0, tags=auth_tags)
                raise
            self.service_check(_SERVICE_CHECK_CAN_LOGIN, self.OK, tags=auth_tags)
            self.gauge("can_login", 1, tags=auth_tags)

        try:
            response = self._client.request("get", f"{self._client.api_endpoint}/config/servers")
            response.raise_for_status()
            servers = response.json()
        except Exception as e:
            auth_tags = self._auth_tags()
            self.service_check(
                _SERVICE_CHECK_CAN_CONNECT,
                self.CRITICAL,
                tags=auth_tags,
                message=f"Failed to connect to Control-M API: {e}",
            )
            self.gauge("can_connect", 0, tags=auth_tags)
            raise

        auth_tags = self._auth_tags()
        self.service_check(_SERVICE_CHECK_CAN_CONNECT, self.OK, tags=auth_tags)
        self.gauge("can_connect", 1, tags=auth_tags)

        self._collect_server_health(servers)
        self._collect_metadata(servers)
        self._job_collector.collect()

    def _auth_tags(self) -> list[str]:
        return self._base_tags + [self._client.auth_method_tag()]

    def _collect_server_health(self, servers: Any) -> None:
        # Collect server health from the Control-M API. 1 is up, 0 is down.
        if not isinstance(servers, list):
            return

        for server in servers:
            ctm_server = server.get("name") or server.get("ctm") or server.get("server") or "unknown"
            raw_state = str(server.get("state", "unknown"))
            state_tag = raw_state.lower().replace(" ", "_")
            is_up = 1 if state_tag in UP_STATES else 0
            tags = self._base_tags + [f"ctm_server:{ctm_server}", f"state:{state_tag}"]
            self.gauge("server.up", is_up, tags=tags)

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self, servers: Any) -> None:
        # The /config/servers response is a list of server objects, each with
        # a "version" field (e.g. "9.0.21.080").  Report the first one found.
        if isinstance(servers, list):
            for server in servers:
                version = server.get("version")
                if version:
                    self.set_metadata("version", version)
                    self.log.debug("Collected Control-M version: %s", version)
                    return
        self.log.debug("Could not determine Control-M version from /config/servers response")
