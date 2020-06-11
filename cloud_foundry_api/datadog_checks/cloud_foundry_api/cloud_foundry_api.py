# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import time
from typing import Any, Dict, List, Tuple

import semver
from requests.exceptions import HTTPError, RequestException
from six.moves.urllib_parse import urljoin, urlparse

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.base.types import Event

from .constants import (
    API_SERVICE_CHECK_NAME,
    DEFAULT_EVENT_FILTER,
    DEFAULT_PAGE_SIZE,
    MAX_LOOKBACK_SECONDS,
    MAX_PAGE_SIZE_V2,
    MAX_PAGE_SIZE_V3,
    MIN_V3_VERSION,
    TOCKEN_EXPIRATION_BUFFER,
    UAA_SERVICE_CHECK_NAME,
)
from .utils import get_next_url, parse_event


class CloudFoundryApiCheck(AgentCheck):
    __NAMESPACE__ = "cloud_foundry_api"

    def __init__(self, name, init_config, instances):
        super(CloudFoundryApiCheck, self).__init__(name, init_config, instances)

        # Configuration
        self._api_url = self.instance.get("api_url")
        if not self._api_url:
            raise ConfigurationError("`api_url` parameter is required")
        self._client_id = self.instance.get("client_id")
        if not self._client_id:
            raise ConfigurationError("`client_id` parameter is required")
        self._client_secret = self.instance.get("client_secret")
        if not self._client_secret:
            raise ConfigurationError("`client_secret` parameter is required")
        self._event_filter = ",".join(self.instance.get("event_filter", DEFAULT_EVENT_FILTER))
        self._tags = self.instance.get("tags", [])
        self._per_page = self.instance.get("results_per_page", DEFAULT_PAGE_SIZE)

        self._last_event_guid = ""
        self._last_event_ts = 0
        self._oauth_token = ""
        self._token_expiration = 0
        self._api_version, self._uaa_url = self.discover_api()

    def discover_api(self):
        # type: () -> Tuple[str, str]
        self.log.info("Discovering Cloud Foundry API version and authentication endpoint")
        try:
            res = self.http.get(self._api_url)
        except RequestException:
            self.log.exception("Error connecting to the API server")
            raise
        try:
            res.raise_for_status()
        except HTTPError:
            self.log.exception("Error querying API information: response: %s", res.text)
            raise
        try:
            payload = res.json()
        except ValueError:
            self.log.exception("Error decoding API information: response: %s", res.text)
            raise

        links = payload.get("links")
        if not links:
            raise CheckException("Unable to inspect API information from payload {}".format(payload))

        api_v3_version = "0.0.0"
        try:
            api_v3_version = links["cloud_controller_v3"]["meta"]["version"]
        except Exception:
            self.log.debug("cloud_controller_v3 information not found, defaulting to v2")

        try:
            uaa_url = links["uaa"]["href"]
        except Exception:
            raise CheckException("Unable to collect API version and/or UAA URL from links {}".format(links))

        api_version = "v2"
        if semver.parse_version_info(api_v3_version) >= MIN_V3_VERSION:
            api_version = "v3"
        self.log.info("Discovered API `%s` and UAA URL `%s`", api_version, uaa_url)
        return api_version, uaa_url

    def get_oauth_token(self):
        # type: () -> None
        if self._oauth_token is not None and self._token_expiration - TOCKEN_EXPIRATION_BUFFER > int(time.time()):
            return
        self.log.info("Refreshing access token")
        sc_tags = [
            "uaa_url:{}".format(urlparse(self._uaa_url)[1]),
            "api_url:{}".format(urlparse(self._api_url)[1]),
        ] + self._tags
        try:
            res = self.http.get(
                # Make sure to have at least one trailing slash to avoid surprises with urljoin
                urljoin(self._uaa_url + "/", "oauth/token"),
                auth=(self._client_id, self._client_secret),
                params={"grant_type": "client_credentials"},
            )
        except RequestException:
            self.log.exception("Error connecting to the UAA server")
            self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
            raise
        try:
            res.raise_for_status()
        except HTTPError:
            self.log.exception("Error authenticating to the UAA server: response: %s", res.text)
            self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
            raise
        try:
            payload = res.json()
        except ValueError:
            self.log.exception("Error decoding response from the UAA server: response: %s", res.text)
            self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
            raise

        self._oauth_token = payload["access_token"]
        self._token_expiration = int(time.time()) + payload["expires_in"]
        self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.OK, tags=sc_tags)

    def scroll_pages(self, url, params, headers, additional_tags):
        # type: (str, Dict[str, Any], Dict[str, str], List[str]) -> Dict[str, Event]
        page = 1
        events = {}  # type: Event
        scroll = True
        sc_tags = ["api_url:{}".format(urlparse(self._api_url)[1])] + self._tags
        while scroll:
            params = copy.deepcopy(params)
            params["page"] = page
            self.log.debug("Fetching events page %s", page)
            try:
                res = self.http.get(url, params=params, headers=headers)
            except RequestException:
                self.log.exception("Error connecting to the Cloud Controller API")
                self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                return events
            try:
                res.raise_for_status()
            except HTTPError:
                self.log.exception("Error querying list of events: response %s", res.text)
                self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                return events
            try:
                payload = res.json()
            except ValueError:
                self.log.exception("Error decoding response from the Cloud Controller API: response %s", res.text)
                self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                return events

            for cf_event in payload.get("resources", []):
                try:
                    dd_event, event_guid, event_ts = parse_event(cf_event, self._api_version, additional_tags)
                except (ValueError, KeyError):
                    self.log.exception("Could not parse event %s", cf_event)
                    continue
                # Stop going through events if we've reached one we've already fetched or if we went back in time enough
                if event_guid == self._last_event_guid or int(time.time()) - event_ts > MAX_LOOKBACK_SECONDS:
                    scroll = False
                    break
                # Store the event at which we want to stop on the next check run: the most recent of the current run
                if event_ts > self._last_event_ts:
                    self._last_event_guid = event_guid
                    self._last_event_ts = event_ts
                # Make sure we don't send duplicate events in case the pagination gets shifted by new events
                if event_guid not in events:
                    events[event_guid] = dd_event
            # Fetch next page if any
            next_url = get_next_url(payload, self._api_version)
            if not next_url or not scroll:
                break
            page += 1
        self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.OK, tags=sc_tags)
        return events

    def get_events(self, additional_tags):
        # type: (List[str]) -> Dict[str, Event]
        self.get_oauth_token()
        if self._api_version == "v2":
            params = {
                "q": "type IN {}".format(self._event_filter),
                "results-per-page": min(self._per_page, MAX_PAGE_SIZE_V2),
                "order-direction": "desc",
                "order-by": "timestamp",
            }
            headers = {"Authorization": "Bearer {}".format(self._oauth_token)}
            url = "{}/v2/events".format(self._api_url)
            return self.scroll_pages(url, params, headers, additional_tags)
        elif self._api_version == "v3":
            params = {
                "types": self._event_filter,
                "per_page": min(self._per_page, MAX_PAGE_SIZE_V3),
                "order_by": "-created_at",
            }
            headers = {"Authorization": "Bearer {}".format(self._oauth_token)}
            # Make sure to have at least one trailing slash to avoid surprises with urljoin
            url = urljoin(self._api_url + "/", "v3/audit_events")
            return self.scroll_pages(url, params, headers, additional_tags)

        self.log.error("Unknown api version `%s`", self._api_version)
        return {}

    def check(self, _):
        # type: (Dict[str, Any]) -> None
        tags = ["api_url:{}".format(urlparse(self._api_url)[1])] + self._tags
        events = self.get_events(tags)
        self.count("events.count", len(events), tags=tags)
        for event in events.values():
            self.event(event)
