# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict

import requests
from pyVmomi import vim
from vmware.vapi.vsphere.client import create_vsphere_client

from .api import APIConnectionError, smart_retry

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

        self._client = None
        self.smart_connect()

    def smart_connect(self):
        """
        Create an authenticated stub configuration object that can be used to issue
        requests against vCenter.
        Returns a stub_config that stores the session identifier that can be used
        to issue authenticated requests against vCenter.
        """

        session = requests.Session()
        session.verify = self.config.ssl_verify
        session.cert = self.config.ssl_capath

        try:
            client = create_vsphere_client(
                session=session,
                username=self.config.username,
                password=self.config.password,
                server=self.config.hostname,
            )
        except Exception as e:
            err_msg = "Connection to {} failed, hostname: {}".format(self.config.hostname, e)
            raise APIConnectionError(err_msg)

        self._client = client

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
        tag_associations = self._get_tag_associations(tag_ids)

        # Initialise resource_tags
        resource_tags = {resource_type: defaultdict(list) for resource_type in MOR_TYPE_MAPPING.values()}

        for tag_asso in tag_associations:
            tag = tags[tag_asso.tag_id]
            for resource_asso in tag_asso.object_ids:
                resource_type = MOR_TYPE_MAPPING.get(resource_asso.type)
                if not resource_type:
                    self.log.debug(
                        "Invalid resource type `%s`. Valid resource types are: %s",
                        resource_asso.type,
                        MOR_TYPE_MAPPING.keys(),
                    )
                    continue
                resource_tags[resource_type][resource_asso.id].append(tag)

        return resource_tags

    def _get_tag_associations(self, tag_ids):
        tag_associations = self._client.tagging.TagAssociation.list_attached_objects_on_tags(tag_ids)
        return tag_associations

    def _get_categories(self):
        category_ids = self._client.tagging.Category.list()
        categories = {}
        for category_id in category_ids:
            cat = self._client.tagging.Category.get(category_id)
            categories[category_id] = cat.name
        return categories

    def _get_tags(self, categories):
        """
        Create tags using vSphere tag category as key and vSphere tag name as value.

            <TAG_CATEGORY>:<TAG_NAME>

        Examples:
            - os_type:windows
            - application_name:my_app

        Taging best practices:
        https://www.vmware.com/content/dam/digitalmarketing/vmware/en/pdf/techpaper/performance/tagging-vsphere67-perf.pdf
        """
        tag_ids = self._client.tagging.Tag.list()
        tags = {}
        for tag_id in tag_ids:
            tag = self._client.tagging.Tag.get(tag_id)
            cat_name = categories.get(tag.category_id, 'unknown_category')
            tags[tag_id] = "{}:{}".format(cat_name, tag.name)
        return tags
