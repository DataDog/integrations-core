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
        Create a vSphere client.
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
            err_msg = "Connection to vSphere Rest API failed for host {}: {}".format(self.config.hostname, e)
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
        self.log.debug("Fetched tag associations: %s", tag_associations)

        # Initialise resource_tags
        resource_tags = {resource_type: defaultdict(list) for resource_type in MOR_TYPE_MAPPING.values()}

        for tag_asso in tag_associations:
            tag = tags[tag_asso.tag_id]
            for resource_asso in tag_asso.object_ids:
                resource_type = MOR_TYPE_MAPPING.get(resource_asso.type)
                if not resource_type:
                    continue
                resource_tags[resource_type][resource_asso.id].append(tag)
        self.log.debug("Result resource tags: %s", resource_tags)
        return resource_tags

    def _get_tag_associations(self, tag_ids):
        """
        :rtype: :class:`list` of :class:`com.vmware.cis.tagging_client.TagAssociation.TagToObjects`
        :return: tag_associations: the structure of the tag associations is as follow:
            [
                TagToObjects(tag_id='tag_id_1', object_ids=[DynamicID(type='VirtualMachine', id='VM4-4-1')]),
                TagToObjects(tag_id='tag_id_2', object_ids=[DynamicID(type='VirtualMachine', id='VM4-4-1')]),
                ...
            ]
        """
        tag_associations = self._client.tagging.TagAssociation.list_attached_objects_on_tags(tag_ids)
        return tag_associations

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
        category_ids = self._client.tagging.Category.list()
        categories = {}
        for category_id in category_ids:
            cat = self._client.tagging.Category.get(category_id)
            categories[category_id] = cat.name
        return categories

    def _get_tags(self, categories):
        """
        Create tags using vSphere tags prefix + vSphere tag category name as key and vSphere tag name as value.

            <VSPHERE_TAGS_PREFIX><TAG_CATEGORY>:<TAG_NAME>

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
            tags[tag_id] = "{}{}:{}".format(self.config.vsphere_tags_prefix, cat_name, tag.name)
        return tags
