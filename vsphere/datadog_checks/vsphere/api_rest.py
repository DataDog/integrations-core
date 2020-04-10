# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
from collections import defaultdict
from typing import Any, Dict, Iterator, List, Set

from pyVmomi import vim
from six import iteritems

from datadog_checks.base.log import CheckLoggingAdapter
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.vsphere.config import VSphereConfig
from datadog_checks.vsphere.constants import ALL_RESOURCES_WITH_METRICS
from datadog_checks.vsphere.types import ResourceTags, TagAssociation

from .api import APIResponseError

MOR_TYPE_MAPPING_FROM_STRING = {
    'HostSystem': vim.HostSystem,
    'VirtualMachine': vim.VirtualMachine,
    'Datacenter': vim.Datacenter,
    'Datastore': vim.Datastore,
    'ClusterComputeResource': vim.ClusterComputeResource,
}

MOR_TYPE_MAPPING_TO_STRING = {v: k for k, v in iteritems(MOR_TYPE_MAPPING_FROM_STRING)}


class VSphereRestAPI(object):
    """
    Abstraction class over the vSphere REST api
    """

    def __init__(self, config, log):
        # type: (VSphereConfig, CheckLoggingAdapter) -> None
        self.config = config
        self.log = log
        self._client = VSphereRestClient(config, log)
        self.smart_connect()

    def smart_connect(self):
        # type: () -> None
        """
        Connect to vSphere client.
        """
        self._client.connect_session()

    def make_batch(self, mors):
        # type: (Iterator[vim.ManagedEntity]) -> Iterator[List[vim.ManagedEntity]]
        batch = []  # type: List[vim.ManagedEntity]
        size = self.config.batch_tags_collector_size
        for mor in mors:
            if len(batch) == size:
                yield batch
                batch = []
            batch.append(mor)
        if batch:
            yield batch

    # Don't retry, mors is an iterator and will be consumed during the function call.
    def get_resource_tags_for_mors(self, mors):
        # type: (Iterator[vim.ManagedEntity]) -> ResourceTags
        """
        Get resource tags.

        Response structure:

            {
                <RESOURCE_TYPE>: {
                    <RESOURCE_MOR_ID>: ['<CATEGORY_NAME>:<TAG_NAME>', ...]
                },
                ...
            }
        """
        tag_associations = []
        for mors_batch in self.make_batch(mors):
            batch_tag_associations = self._client.tagging_tag_association_list_attached_tags_on_objects(mors_batch)
            tag_associations.extend(batch_tag_associations)

        self.log.debug("Fetched tag associations: %s", tag_associations)

        # Initialise resource_tags
        resource_tags = {
            resource_type: defaultdict(list) for resource_type in ALL_RESOURCES_WITH_METRICS
        }  # type: ResourceTags

        all_tag_ids = set()
        for tag_asso in tag_associations:
            all_tag_ids.update(tag_asso["tag_ids"])

        tags = self._get_tags(all_tag_ids)

        for tag_asso in tag_associations:
            mor_id = tag_asso["object_id"]["id"]
            mor_type = MOR_TYPE_MAPPING_FROM_STRING[tag_asso["object_id"]["type"]]
            mor_tag_ids = tag_asso["tag_ids"]
            for mor_tag_id in mor_tag_ids:
                if mor_tag_id not in tags:
                    self.log.debug("MOR tag id '%s' was not found in response, ignoring.", mor_tag_id)
                    continue
                resource_tags[mor_type][mor_id].append(tags[mor_tag_id])

        self.log.debug("Result resource tags: %s", resource_tags)
        return resource_tags

    def _get_tags(self, tag_ids):
        # type: (Set[str]) -> Dict[str, str]
        """
        Create tags using vSphere tags prefix + vSphere tag category name as key and vSphere tag name as value.

            <TAGS_PREFIX><TAG_CATEGORY>:<TAG_NAME>

        Examples:
            - os_type:windows
            - application_name:my_app

        Taging best practices:
        https://www.vmware.com/content/dam/digitalmarketing/vmware/en/pdf/techpaper/performance/tagging-vsphere67-perf.pdf
        """
        tags = {}
        categories = {}
        for tag_id in tag_ids:
            tag = self._client.tagging_tags_get(tag_id)
            category_id = tag["category_id"]
            if category_id not in categories:
                categories[category_id] = self._client.tagging_category_get(category_id)
            category_name = categories[category_id]["name"]
            tags[tag_id] = "{}{}:{}".format(self.config.tags_prefix, category_name, tag['name'])
        return tags


class VSphereRestClient(object):
    """
    Custom vSphere Rest API Client
    """

    JSON_REQUEST_HEADERS = {'Content-Type': 'application/json'}

    def __init__(self, config, log):
        # type: (VSphereConfig, CheckLoggingAdapter) -> None
        self.log = log
        http_config = {
            'username': config.username,
            'password': config.password,
            'tls_ca_cert': config.ssl_capath,
            'tls_verify': config.ssl_verify,
            'tls_ignore_warning': config.tls_ignore_warning,
        }
        self._api_base_url = "https://{}/rest/com/vmware/cis/".format(config.hostname)
        self._http = RequestsWrapper(http_config, {})

    def connect_session(self):
        # type: () -> None
        session_token = self.session_create()

        if not session_token:
            raise APIResponseError("Failed to retrieve session token")

        self._http.options['headers']['vmware-api-session-id'] = session_token

    def session_create(self):
        # type: () -> str
        """
        Create session token
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/session.create-operation.html
        """
        session_token = self._request_json("session", method="post", extra_headers=self.JSON_REQUEST_HEADERS,)
        return session_token

    def tagging_category_get(self, category_id):
        # type: (str) -> Dict[str, Any]
        """
        Get one category
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/category.get-operation.html
        """
        return self._request_json("tagging/category/id:{}".format(category_id))

    def tagging_tags_get(self, tag_id):
        # type: (str) -> Dict[str, Any]
        """
        Get one tag
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/tag.get-operation.html
        """
        return self._request_json("tagging/tag/id:{}".format(tag_id))

    def tagging_tag_association_list_attached_tags_on_objects(self, mors):
        # type: (List[vim.ManagedEntity]) -> List[TagAssociation]
        """
        Get all tags identifiers for a given set of objects
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/tag_association.list_attached_tags_on_objects-operation.html
        """
        payload = {"object_ids": [{"id": mor._moId, "type": MOR_TYPE_MAPPING_TO_STRING[type(mor)]} for mor in mors]}
        tag_associations = self._request_json(
            "tagging/tag-association?~action=list-attached-tags-on-objects",
            method="post",
            data=json.dumps(payload),
            extra_headers=self.JSON_REQUEST_HEADERS,
        )
        return tag_associations

    def _request_json(self, endpoint, method='get', **options):
        # type: (str, str, **Any) -> Any
        url = self._api_base_url + endpoint
        resp = getattr(self._http, method)(url, **options)
        resp.raise_for_status()

        data = resp.json()
        if 'value' not in data:
            raise APIResponseError("Missing `value` element in response for url: {}".format(url))

        return data['value']
