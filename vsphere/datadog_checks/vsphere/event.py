# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import re
from datetime import datetime
from hashlib import md5

from pyVmomi import vim

from datadog_checks.base import ensure_unicode

from .constants import (
    DEFAULT_EVENT_RESOURCES,
    EXCLUDE_FILTERS,
    MOR_TYPE_AS_STRING,
    PER_RESOURCE_EVENTS,
    SOURCE_TYPE,
)


class VSphereEvent(object):
    UNKNOWN = 'unknown'

    def __init__(self, raw_event, event_config, tags, event_resource_filters, exclude_filters=EXCLUDE_FILTERS):
        self.raw_event = raw_event
        if self.raw_event and self.raw_event.__class__.__name__.startswith('vim.event'):
            self.event_type = self.raw_event.__class__.__name__[10:]
        else:
            self.event_type = VSphereEvent.UNKNOWN

        self.timestamp = int((self.raw_event.createdTime.replace(tzinfo=None) - datetime(1970, 1, 1)).total_seconds())
        self.payload = {
            "timestamp": self.timestamp,
            "event_type": SOURCE_TYPE,
            "source_type_name": SOURCE_TYPE,
            "tags": tags[:],
        }
        if event_config is None:
            self.event_config = {}
        else:
            self.event_config = event_config
        self.exclude_filters = exclude_filters
        self.event_resource_filters = event_resource_filters

    def _is_filtered(self):
        # Filter the unwanted types
        if self.event_type in PER_RESOURCE_EVENTS:
            # Get the entity type/name
            self.entity_type = self.raw_event.entity.entity.__class__

            self.host_type = MOR_TYPE_AS_STRING.get(self.entity_type, None)
            if self.host_type not in self.event_resource_filters:
                return True

        if self.event_type not in self.exclude_filters:
            return True

        filters = self.exclude_filters[self.event_type]
        for f in filters:
            if re.search(f, self.raw_event.fullFormattedMessage):
                return True

        return False

    def get_datadog_payload(self):
        if self._is_filtered():
            return None

        transform_method = getattr(self, 'transform_%s' % self.event_type.lower(), None)
        if callable(transform_method):
            return transform_method()

        # Default event transformation
        self.payload["msg_title"] = u"{0}".format(self.event_type)
        self.payload["msg_text"] = u"@@@\n{0}\n@@@".format(self.raw_event.fullFormattedMessage)

        return self.payload

    def transform_vmbeinghotmigratedevent(self):
        self.payload["msg_title"] = "VM {} is being migrated".format(self.raw_event.vm.name)
        self.payload["msg_text"] = "{user} has launched a hot migration of this virtual machine:\n".format(
            user=self.raw_event.userName
        )
        changes = []
        pre_host = self.raw_event.host.name
        new_host = self.raw_event.destHost.name
        pre_dc = self.raw_event.datacenter.name
        new_dc = self.raw_event.destDatacenter.name
        pre_ds = self.raw_event.ds.name
        new_ds = self.raw_event.destDatastore.name
        if pre_host == new_host:
            changes.append(u"- No host migration: still {0}".format(new_host))
        else:
            # Insert in front if it's a change
            changes = [u"- Host MIGRATION: from {0} to {1}".format(pre_host, new_host)] + changes
        if pre_dc == new_dc:
            changes.append(u"- No datacenter migration: still {0}".format(new_dc))
        else:
            # Insert in front if it's a change
            changes = [u"- Datacenter MIGRATION: from {0} to {1}".format(pre_dc, new_dc)] + changes
        if pre_ds == new_ds:
            changes.append(u"- No datastore migration: still {0}".format(new_ds))
        else:
            # Insert in front if it's a change
            changes = [u"- Datastore MIGRATION: from {0} to {1}".format(pre_ds, new_ds)] + changes

        self.payload["msg_text"] += "\n".join(changes)

        self.payload['host'] = self.raw_event.vm.name
        self.payload['tags'].extend(
            [
                'vsphere_host:{}'.format(ensure_unicode(pre_host)),
                'vsphere_host:{}'.format(ensure_unicode(new_host)),
                'vsphere_datacenter:{}'.format(ensure_unicode(pre_dc)),
                'vsphere_datacenter:{}'.format(ensure_unicode(new_dc)),
            ]
        )
        return self.payload

    def transform_alarmstatuschangedevent(self):
        if self.event_config.get('collect_vcenter_alarms') is None:
            return None

        def get_transition(before, after):
            vals = {'gray': -1, 'green': 0, 'yellow': 1, 'red': 2}
            before = before.lower()
            after = after.lower()
            if before not in vals or after not in vals:
                return None
            if vals[before] < vals[after]:
                return 'Triggered'
            return 'Recovered'

        TO_ALERT_TYPE = {'green': 'success', 'yellow': 'warning', 'red': 'error', 'gray': 'info'}

        def get_agg_key(alarm_event):
            return 'h:{0}|dc:{1}|a:{2}'.format(
                md5(alarm_event.entity.name.encode('utf-8')).hexdigest()[:10],
                md5(alarm_event.datacenter.name.encode('utf-8')).hexdigest()[:10],
                md5(alarm_event.alarm.name.encode('utf-8')).hexdigest()[:10],
            )

        host_name = None
        entity_name = self.raw_event.entity.name

        # for backwards compatibility, vm host type is capitalized
        if self.entity_type == vim.VirtualMachine:
            self.host_type = 'VM'

        if self.entity_type == vim.VirtualMachine or self.entity_type == vim.HostSystem:
            host_name = entity_name
        if self.host_type is None:
            return None

        # Need a getattr because from is a reserved keyword...
        trans_before = getattr(self.raw_event, 'from')  # noqa: B009
        trans_after = self.raw_event.to
        transition = get_transition(trans_before, trans_after)
        # Bad transition, we shouldn't have got this transition
        if transition is None:
            return None

        self.payload['msg_title'] = u"[{transition}] {monitor} on {host_type} {entity_name} is now {status}".format(
            transition=transition,
            monitor=self.raw_event.alarm.name,
            host_type=self.host_type,
            entity_name=entity_name,
            status=trans_after,
        )
        self.payload['alert_type'] = TO_ALERT_TYPE[trans_after]
        self.payload['event_object'] = get_agg_key(self.raw_event)
        self.payload['msg_text'] = (
            "vCenter monitor status changed on this alarm, "
            "it was {before} and it's now {after}.".format(before=trans_before, after=trans_after)
        )
        if host_name is not None:
            self.payload['host'] = host_name

        # VMs and hosts submit these as host tags
        if self.host_type.lower() not in DEFAULT_EVENT_RESOURCES:
            self.payload['tags'].extend(
                [
                    'vsphere_type:{}'.format(self.host_type),
                    'vsphere_resource:{}'.format(entity_name),
                ]
            )

        return self.payload

    def transform_vmmessageevent(self):
        self.payload["msg_title"] = u"VM {0} is reporting".format(self.raw_event.vm.name)
        self.payload["msg_text"] = u"@@@\n{0}\n@@@".format(self.raw_event.fullFormattedMessage)
        self.payload['host'] = self.raw_event.vm.name
        return self.payload

    def transform_vmmigratedevent(self):
        self.payload["msg_title"] = u"VM {0} has been migrated".format(self.raw_event.vm.name)
        self.payload["msg_text"] = u"@@@\n{0}\n@@@".format(self.raw_event.fullFormattedMessage)
        self.payload['host'] = self.raw_event.vm.name
        return self.payload

    def transform_vmpoweredoffevent(self):
        self.payload["msg_title"] = u"VM {0} has been powered OFF".format(self.raw_event.vm.name)
        self.payload["msg_text"] = (
            u"""{user} has powered off this virtual machine. It was running on:
- datacenter: {dc}
- host: {host}
""".format(
                user=self.raw_event.userName, dc=self.raw_event.datacenter.name, host=self.raw_event.host.name
            )
        )
        self.payload['host'] = self.raw_event.vm.name
        return self.payload

    def transform_vmpoweredonevent(self):
        self.payload["msg_title"] = u"VM {0} has been powered ON".format(self.raw_event.vm.name)
        self.payload["msg_text"] = (
            u"""{user} has powered on this virtual machine. It is running on:
- datacenter: {dc}
- host: {host}
""".format(
                user=self.raw_event.userName, dc=self.raw_event.datacenter.name, host=self.raw_event.host.name
            )
        )
        self.payload['host'] = self.raw_event.vm.name
        return self.payload

    def transform_vmresumingevent(self):
        self.payload["msg_title"] = u"VM {0} is RESUMING".format(self.raw_event.vm.name)
        self.payload["msg_text"] = u"""{user} has resumed {vm}. It will soon be powered on.""".format(
            user=self.raw_event.userName, vm=self.raw_event.vm.name
        )
        self.payload['host'] = self.raw_event.vm.name
        return self.payload

    def transform_vmsuspendedevent(self):
        self.payload["msg_title"] = u"VM {0} has been SUSPENDED".format(self.raw_event.vm.name)
        self.payload["msg_text"] = (
            u"""{user} has suspended this virtual machine. It was running on:
- datacenter: {dc}
- host: {host}
""".format(
                user=self.raw_event.userName, dc=self.raw_event.datacenter.name, host=self.raw_event.host.name
            )
        )
        self.payload['host'] = self.raw_event.vm.name
        return self.payload

    def transform_vmreconfiguredevent(self):
        self.payload["msg_title"] = u"VM {0} configuration has been changed".format(self.raw_event.vm.name)
        self.payload["msg_text"] = u"{user} saved the new configuration:\n@@@\n".format(user=self.raw_event.userName)
        # Add lines for configuration change don't show unset, that's hacky...
        config_change_lines = [
            line for line in self.raw_event.configSpec.__repr__().splitlines() if 'unset' not in line
        ]
        self.payload["msg_text"] += u"\n".join(config_change_lines)
        self.payload["msg_text"] += u"\n@@@"
        self.payload['host'] = self.raw_event.vm.name
        return self.payload
