# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import json
from datetime import datetime

from mock import Mock, MagicMock
from pyVmomi import vim


HERE = os.path.abspath(os.path.dirname(__file__))


class MockedMOR(Mock):
    """
    Helper, generate a mocked Managed Object Reference (MOR) from the given attributes.
    """
    def __init__(self, **kwargs):
        # Deserialize `spec`
        if 'spec' in kwargs:
            kwargs['spec'] = getattr(vim, kwargs['spec'])

        # Mocking
        super(MockedMOR, self).__init__(**kwargs)

        self.name = kwargs.get('name')
        self.parent = None
        self.parent_name = kwargs.get('parent_name', None)
        self.customValue = []
        power_state = kwargs.get('runtime.powerState', None)
        host_name = kwargs.get('runtime.host_name', None)
        if power_state:
            self.runtime_powerState = getattr(vim.VirtualMachinePowerState, power_state)
        if host_name:
            self.runtime_host_name = host_name

        if kwargs.get('label', False):
            self.customValue.append(Mock(value="DatadogMonitored"))


def create_topology(topology_json):
    objects = []
    with open(topology_json) as f:
        topology = json.loads(f.read())
        for obj_desc in topology:
            obj = MockedMOR(**obj_desc)
            objects.append(obj)
        # Assign parent object based on name, as well as runtime host for VMs
        for obj in objects:
            if obj.parent_name:
                obj.parent = next(obj2 for obj2 in objects if obj2.name == obj.parent_name)
            if hasattr(obj, "runtime_host_name"):
                obj.runtime_host = next(obj2 for obj2 in objects if obj2.name == obj.runtime_host_name)

        return objects


def retrieve_properties_mock(all_mors):
    objects = []
    properties_res = MagicMock(objects=objects, token=None)
    mor_properties = ["name", "parent", "customValue", "runtime_powerState", "runtime_host"]
    for mor in all_mors:
        prop_set = []
        for prop_name in mor_properties:
            try:
                prop = MagicMock()
                prop.val = getattr(mor, prop_name)
                prop.name = prop_name.replace("_", ".")
                prop_set.append(prop)
            except AttributeError:
                # Only VMs have powerState or host attribute
                continue

        objects.append(MagicMock(obj=mor, propSet=prop_set))

    return properties_res


def assertMOR(check, instance, name=None, spec=None, tags=None, count=None, subset=False):
    """
    Helper, assertion on vCenter Manage Object References.
    """
    instance_name = instance['name']
    candidates = []

    mor_list = [mor for _, mors in check.mor_objects_queue._objects_queue[instance_name].iteritems() for mor in mors]

    for mor in mor_list:
        if name is not None and name != mor['hostname']:
            continue

        if spec is not None and spec != mor['mor_type']:
            continue

        if tags is not None:
            if subset:
                if not set(tags).issubset(set(mor['tags'])):
                    continue
            elif set(tags) != set(mor['tags']):
                continue

        candidates.append(mor)

    # Assertions
    if count:
        assert count == len(candidates)
    else:
        assert len(candidates)


def disable_thread_pool(check):
    """
    Disable the thread pool on the check instance
    """
    check.pool = MagicMock(apply_async=lambda func, args: func(*args))
    check.pool._workq.qsize.return_value = 0
    check.pool_started = True  # otherwise the mock will be overwritten
    return check


def get_mocked_server():
    """
    Return a mocked Server object
    """
    # mock pyvmomi stuff
    all_mors = create_topology(os.path.join(HERE, 'fixtures', 'vsphere_topology.json'))
    root_folder_mock = next(mor for mor in all_mors if mor.name == "rootFolder")
    event_mock = MagicMock(createdTime=datetime.now())
    eventmanager_mock = MagicMock(latestEvent=event_mock)
    property_collector_mock = MagicMock()
    property_collector_mock.RetrievePropertiesEx.return_value = retrieve_properties_mock(all_mors)
    content_mock = MagicMock(
        eventManager=eventmanager_mock, propertyCollector=property_collector_mock, rootFolder=root_folder_mock
    )
    # assemble the mocked server
    server_mock = MagicMock()
    server_mock.configure_mock(**{
        'RetrieveContent.return_value': content_mock,
        'content': content_mock
    })
    return server_mock
