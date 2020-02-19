# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
from collections import defaultdict

from pyVmomi import vim

from datadog_checks.base.utils.http import RequestsWrapper

from .api import APIResponseError, smart_retry

MOR_TYPE_MAPPING = {
    'HostSystem': vim.HostSystem,
    'VirtualMachine': vim.VirtualMachine,
    'Datacenter': vim.Datacenter,
    'Datastore': vim.Datastore,
    'ClusterComputeResource': vim.ClusterComputeResource,
}


class VSphereRestAPI(object):
    """
    Abstraction class over the vSphere REST api using the vsphere-automation-sdk-python library
    """

    def __init__(self, config, log):
        self.config = config
        self.log = log
        self._client = VSphereRestClient(config, log)
        self.smart_connect()

    def smart_connect(self):
        """
        Connect to vSphere client.
        """
        self._client.connect_session()

    @smart_retry
    def get_resource_tags(self):
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
        categories = self._get_categories()
        tags = self._get_tags(categories)
        tag_ids = list(tags.keys())
        tag_associations = self._client.tagging_tag_association_list_attached_objects_on_tags(tag_ids)
        self.log.debug("Fetched tag associations: %s", tag_associations)

        # Initialise resource_tags
        resource_tags = {resource_type: defaultdict(list) for resource_type in MOR_TYPE_MAPPING.values()}

        for tag_asso in tag_associations:
            tag = tags[tag_asso['tag_id']]
            for resource_asso in tag_asso['object_ids']:
                resource_type = MOR_TYPE_MAPPING.get(resource_asso['type'])
                if not resource_type:
                    continue
                resource_tags[resource_type][resource_asso['id']].append(tag)
        self.log.debug("Result resource tags: %s", resource_tags)
        return resource_tags

    def _get_categories(self):
        """
        Returns a dict of categories with category id as key and category name as value.

        :return: categories: the structure of the categories is as follow:
            {
                <CATEGORY_ID>: <CATEGORY_NAME>,
                <CATEGORY_ID>: <CATEGORY_NAME>,
                ...
            }
        """
        category_ids = self._client.tagging_category_list()
        categories = {}
        for category_id in category_ids:
            cat = self._client.tagging_category_get(category_id)
            categories[category_id] = cat['name']
        return categories

    def _get_tags(self, categories):
        """
        Create tags using vSphere tags prefix + vSphere tag category name as key and vSphere tag name as value.

            <TAGS_PREFIX><TAG_CATEGORY>:<TAG_NAME>

        Examples:
            - os_type:windows
            - application_name:my_app

        Taging best practices:
        https://www.vmware.com/content/dam/digitalmarketing/vmware/en/pdf/techpaper/performance/tagging-vsphere67-perf.pdf
        """
        tag_ids = self._client.tagging_tags_list()
        tags = {}
        for tag_id in tag_ids:
            tag = self._client.tagging_tags_get(tag_id)
            cat_name = categories.get(tag['category_id'], 'unknown_category')
            tags[tag_id] = "{}{}:{}".format(self.config.tags_prefix, cat_name, tag['name'])
        return tags


class VSphereRestClient(object):
    """
    Custom vSphere Rest API Client
    """

    JSON_REQUEST_HEADERS = {'Content-Type': 'application/json'}

    def __init__(self, config, log):
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
        session_token = self.session_create("session")

        if not session_token:
            raise APIResponseError("Failed to retrieve session token")

        self._http.options['headers']['vmware-api-session-id'] = session_token

    def session_create(self, tag_ids):
        """
        Create session token
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/session.create-operation.html
        """
        session_token = self._request_json("session", method="post", extra_headers=self.JSON_REQUEST_HEADERS,)
        return session_token

    def tagging_category_list(self):
        """
        Get list of categories
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/category.list-operation.html
        """
        return self._request_json("tagging/category")

    def tagging_category_get(self, category_id):
        """
        Get one category
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/category.get-operation.html
        """
        return self._request_json("tagging/category/id:{}".format(category_id))

    def tagging_tags_list(self):
        """
        Get list of tags
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/tag.list-operation.html
        """
        return self._request_json("tagging/tag")

    def tagging_tags_get(self, tag_id):
        """
        Get one tag
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/tag.get-operation.html
        """
        return self._request_json("tagging/tag/id:{}".format(tag_id))

    def tagging_tag_association_list_attached_objects_on_tags(self, tag_ids):
        """
        Get tag associations for vSphere resources
        Doc:
        https://vmware.github.io/vsphere-automation-sdk-rest/6.5/operations/com/vmware/cis/tagging/tag_association.list_attached_objects_on_tags-operation.html
        """
        payload = {"tag_ids": tag_ids}
        tag_associations = self._request_json(
            "tagging/tag-association?~action=list-attached-objects-on-tags",
            method="post",
            data=json.dumps(payload),
            extra_headers=self.JSON_REQUEST_HEADERS,
        )
        return tag_associations

    def _request_json(self, endpoint, method='get', **options):
        url = self._api_base_url + endpoint
        resp = getattr(self._http, method)(url, **options)
        resp.raise_for_status()

        data = resp.json()
        if 'value' not in data:
            raise APIResponseError("Missing `value` element in response for url: {}".format(url))

        return data['value']
