# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import time
from typing import Any, Dict, Generator, Tuple  # noqa: F401

from requests.exceptions import HTTPError, RequestException
from semver import VersionInfo
from six.moves.urllib_parse import urlparse

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.base.types import Event  # noqa: F401

from .constants import (
    API_SERVICE_CHECK_NAME,
    DEFAULT_EVENT_FILTER,
    DEFAULT_PAGE_SIZE,
    MAX_LOOKBACK_SECONDS,
    MAX_PAGE_SIZE_V2,
    MAX_PAGE_SIZE_V3,
    MIN_V3_VERSION,
    SOURCE_TYPE_NAME,
    TOCKEN_EXPIRATION_BUFFER,
    UAA_SERVICE_CHECK_NAME,
)
from .utils import date_to_ts, get_next_url, join_url


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

        # Fill up orgs and spaces caches
        self._orgs = self.get_orgs()
        self._spaces = self.get_spaces()

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
        if VersionInfo.parse(api_v3_version) >= MIN_V3_VERSION:
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
                join_url(self._uaa_url, "oauth/token"),
                auth=(self._client_id, self._client_secret),  # SKIP_HTTP_VALIDATION`
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

    def get_auth_header(self):
        self.get_oauth_token()
        return {"Authorization": "Bearer {}".format(self._oauth_token)}

    def get_orgs(self):
        orgs = {}
        headers = self.get_auth_header()
        if self._api_version == "v2":
            params = {
                "results-per-page": MAX_PAGE_SIZE_V2,
            }
            url = join_url(self._api_url, "v2/organizations")
            for orgs_page in self.scroll_api_pages(url, params, headers):
                for org in orgs_page.get("resources", []):
                    try:
                        orgs[org["metadata"]["guid"]] = org["entity"]["name"]
                    except KeyError:
                        self.log.exception("Error parsing org object, skipping: %s", org)
            return orgs
        elif self._api_version == "v3":
            params = {
                "per_page": MAX_PAGE_SIZE_V3,
            }
            url = join_url(self._api_url, "v3/organizations")
            for orgs_page in self.scroll_api_pages(url, params, headers):
                for org in orgs_page.get("resources", []):
                    try:
                        orgs[org["guid"]] = org["name"]
                    except KeyError:
                        self.log.exception("Error parsing org object, skipping: %s", org)
            return orgs

        self.log.error("Unknown api version `%s`", self._api_version)
        return {}

    def get_org_name(self, org_guid):
        if org_guid in self._orgs:
            return self._orgs[org_guid]
        else:
            self.log.debug("Orgs cache miss for %s, fetching from CC API...", org_guid)
            headers = self.get_auth_header()
            url = join_url(self._api_url, "{}/organizations/{}".format(self._api_version, org_guid))
            try:
                res = self.http.get(url, headers=headers)
                res.raise_for_status()
                payload = res.json()
                org_name = ""
                if self._api_version == "v2":
                    org_name = payload["entity"]["name"]
                elif self._api_version == "v3":
                    org_name = payload["name"]
                self._orgs[org_guid] = org_name
                return org_name
            except Exception:
                self.log.exception("Error getting org name for org %s", org_guid)

    def get_spaces(self):
        spaces = {}
        headers = self.get_auth_header()
        if self._api_version == "v2":
            params = {
                "results-per-page": MAX_PAGE_SIZE_V2,
            }
            # Make sure to have at least one trailing slash to avoid surprises with urljoin
            url = join_url(self._api_url, "v2/spaces")
            for spaces_page in self.scroll_api_pages(url, params, headers):
                for space in spaces_page.get("resources", []):
                    try:
                        spaces[space["metadata"]["guid"]] = space["entity"]["name"]
                    except KeyError:
                        self.log.exception("Error parsing space object, skipping: %s", space)
            return spaces
        elif self._api_version == "v3":
            params = {
                "per_page": MAX_PAGE_SIZE_V3,
            }
            url = join_url(self._api_url, "v3/spaces")
            for spaces_page in self.scroll_api_pages(url, params, headers):
                for space in spaces_page.get("resources", []):
                    try:
                        spaces[space["guid"]] = space["name"]
                    except KeyError:
                        self.log.exception("Error parsing space object, skipping: %s", space)
            return spaces

        self.log.error("Unknown api version `%s`", self._api_version)
        return {}

    def get_space_name(self, space_guid):
        if space_guid in self._spaces:
            return self._spaces[space_guid]
        else:
            self.log.debug("Spaces cache miss for %s, fetching from CC API...", space_guid)
            headers = self.get_auth_header()
            url = join_url(self._api_url, "{}/spaces/{}".format(self._api_version, space_guid))
            try:
                res = self.http.get(url, headers=headers)
                res.raise_for_status()
                payload = res.json()
                space_name = ""
                if self._api_version == "v2":
                    space_name = payload["entity"]["name"]
                elif self._api_version == "v3":
                    space_name = payload["name"]
                self._spaces[space_guid] = space_name
                return space_name
            except Exception:
                self.log.exception("Error getting space name for space %s", space_guid)

    def scroll_api_pages(self, url, params, headers):
        # type: (str, Dict[str, Any], Dict[str, str]) -> Generator
        page = 1
        sc_tags = ["api_url:{}".format(urlparse(self._api_url)[1])] + self._tags
        raised = False
        # Wrap inside a try/finally to send the service check even if the generator stops being iterated
        try:
            while True:
                params = copy.deepcopy(params)
                params["page"] = page
                self.log.debug("Fetching events page %s", page)
                try:
                    res = self.http.get(url, params=params, headers=headers)
                except RequestException:
                    self.log.exception("Error connecting to the Cloud Controller API: URL %s", url)
                    self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                    raised = True
                    return
                try:
                    res.raise_for_status()
                except HTTPError:
                    self.log.exception("Error querying Cloud Controller API: URL %s - response %s", url, res.text)
                    self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                    raised = True
                    return
                try:
                    payload = res.json()
                except ValueError:
                    self.log.exception(
                        "Error decoding response from the Cloud Controller API: URL %s - response %s", url, res.text
                    )
                    self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                    raised = True
                    return
                self.log.trace("Payload received from CC API: %s", payload)
                yield payload
                # Fetch next page if any
                next_url = get_next_url(payload, self._api_version)
                if not next_url:
                    break
                page += 1
        finally:
            if not raised:
                self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.OK, tags=sc_tags)

    def scroll_events(self, url, params, headers):
        # type: (str, Dict[str, Any], Dict[str, str]) -> Dict[str, Event]
        events = {}
        scroll = True
        # Memorize the last event guid at which we stopped in the previous check run
        # before we update it during this run
        last_event_guid = self._last_event_guid
        for events_page in self.scroll_api_pages(url, params, headers):
            for cf_event in events_page.get("resources", []):
                try:
                    dd_event, event_guid, event_ts = self.parse_event(cf_event)
                except (ValueError, KeyError):
                    self.log.exception("Could not parse event %s", cf_event)
                    continue
                # Stop going through events if we've reached one we've already fetched or if we went back in time enough
                if event_guid == last_event_guid or int(time.time()) - event_ts > MAX_LOOKBACK_SECONDS:
                    scroll = False
                    break
                # Store the event at which we want to stop on the next check run: the most recent of the current run
                if event_ts > self._last_event_ts:
                    self._last_event_guid = event_guid
                    self._last_event_ts = event_ts
                # Make sure we don't send duplicate events in case the pagination gets shifted by new events
                if event_guid not in events:
                    events[event_guid] = dd_event
            if not scroll:
                break
        return events

    def get_events(self):
        # type: () -> Dict[str, Event]
        headers = self.get_auth_header()
        if self._api_version == "v2":
            params = {
                "q": "type IN {}".format(self._event_filter),
                "results-per-page": min(self._per_page, MAX_PAGE_SIZE_V2),
                "order-direction": "desc",
                "order-by": "timestamp",
            }
            url = join_url(self._api_url, "v2/events")
            return self.scroll_events(url, params, headers)
        elif self._api_version == "v3":
            params = {
                "types": self._event_filter,
                "per_page": min(self._per_page, MAX_PAGE_SIZE_V3),
                "order_by": "-created_at",
            }
            url = join_url(self._api_url, "v3/audit_events")
            return self.scroll_events(url, params, headers)

        self.log.error("Unknown api version `%s`", self._api_version)
        return {}

    def parse_event(self, cf_event):
        # type: (Dict[str, Any]) -> Tuple[Event, str, int]
        dd_event = {}
        event_guid = ""
        event_ts = 0

        if self._api_version == "v2":
            # Parse a v2 event
            # See https://apidocs.cloudfoundry.org/13.2.0/events/list_all_events.html for payload details.
            event_entity = cf_event["entity"]
            event_ts = date_to_ts(event_entity["timestamp"])
            event_guid = cf_event["metadata"]["guid"]

            dd_event = self.build_dd_event(
                event_entity["type"],
                event_guid,
                event_ts,
                event_entity["actor_type"],
                event_entity["actor_name"],
                event_entity["actor"],
                event_entity["actee_type"],
                event_entity["actee_name"],
                event_entity["actee"],
                event_entity.get("space_guid"),  # Some events might not have a space associated
                event_entity.get("organization_guid"),  # Some events might not have an org associated
                event_entity.get("metadata", {}),
            )
        elif self._api_version == "v3":
            # Parse a v3 event
            # See http://v3-apidocs.cloudfoundry.org/version/3.84.0/index.html#list-audit-events for payload details.
            event_ts = date_to_ts(cf_event["created_at"])
            event_guid = cf_event["guid"]
            target = cf_event["target"]
            actor = cf_event["actor"]

            dd_event = self.build_dd_event(
                cf_event["type"],
                event_guid,
                event_ts,
                actor["type"],
                actor["name"],
                actor["guid"],
                target["type"],
                target["name"],
                target["guid"],
                cf_event.get("space", {}).get("guid", ""),  # Some events might not have a space associated
                cf_event.get("organization", {}).get("guid", ""),  # Some events might not have an org associated
                cf_event.get("data", {}),
            )
        return dd_event, event_guid, event_ts

    def build_dd_event(
        self,
        event_type,
        event_guid,
        event_ts,
        actor_type,
        actor_name,
        actor_guid,
        target_type,
        target_name,
        target_guid,
        space_guid,
        org_guid,
        metadata,
    ):
        # type: (str, str, int, str, str, str, str, str, str, str, str, dict) -> Event
        space_id = space_guid if space_guid else "none"
        org_id = org_guid if org_guid else "none"
        # we include both space_guid+space_id and org_guid+org_id; the *_guid are kept for
        # backwards compatibility, the *_id are added to maintain consistency with
        # https://github.com/DataDog/datadog-firehose-nozzle
        tags = [
            "event_type:{}".format(event_type),
            "{}_name:{}".format(target_type, target_name),
            "{}_guid:{}".format(target_type, target_guid),
            "{}_name:{}".format(actor_type, actor_name),
            "{}_guid:{}".format(actor_type, actor_guid),
            "space_guid:{}".format(space_id),
            "space_id:{}".format(space_id),
            "space_name:{}".format(self.get_space_name(space_guid) if space_guid else "none"),
            "org_guid:{}".format(org_id),
            "org_id:{}".format(org_id),
            "org_name:{}".format(self.get_org_name(org_guid) if org_guid else "none"),
        ] + self._tags
        metadata_json = "```\n{}\n```".format(json.dumps(metadata, sort_keys=True, indent=2))
        dd_event = {
            "source_type_name": SOURCE_TYPE_NAME,
            "event_type": event_type,
            "timestamp": event_ts,
            "msg_title": "Event {} happened for {} {}".format(event_type, target_type, target_name),
            "msg_text": "%%% \n Triggered by {} {}\n\nMetadata:\n{} \n %%%".format(
                actor_type, actor_name, metadata_json
            ),
            "priority": "normal",
            "tags": tags,
            "aggregation_key": event_guid,
            # In case we send duplicates for any reason, they'll be aggregated in the app
        }
        return dd_event

    def check(self, _):
        # type: (Dict[str, Any]) -> None
        tags = ["api_url:{}".format(urlparse(self._api_url)[1])] + self._tags
        events = self.get_events()
        self.count("events.count", len(events), tags=tags)
        for event in events.values():
            self.event(event)
