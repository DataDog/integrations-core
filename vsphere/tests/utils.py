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

        # Handle special attributes
        name = kwargs.get('name')
        is_labeled = kwargs.get('label', False)

        self.name = name
        self.parent = None
        self.customValue = []

        if is_labeled:
            self.customValue.append(Mock(value="DatadogMonitored"))


class MockedContainer(Mock):
    TYPES = [vim.Datacenter, vim.Datastore, vim.HostSystem, vim.VirtualMachine]

    def __init__(self, **kwargs):
        # Mocking
        super(MockedContainer, self).__init__(**kwargs)

        self.topology = kwargs.get('topology')
        self.view_idx = 0

    def container_view(self, topology_node, vimtype):
        view = []

        def get_child_topology(attribute):
            entity = getattr(topology_node, attribute)
            try:
                for child in entity:
                    child_topology = self.container_view(child, vimtype)
                    view.extend(child_topology)
            except TypeError:
                child_topology = self.container_view(entity, vimtype)
                view.extend(child_topology)

        if isinstance(topology_node, vimtype):
            view = [topology_node]

        if hasattr(topology_node, 'childEntity'):
            get_child_topology('childEntity')
        elif hasattr(topology_node, 'hostFolder'):
            get_child_topology('hostFolder')
        elif hasattr(topology_node, 'host'):
            get_child_topology('host')
        elif hasattr(topology_node, 'vm'):
            get_child_topology('vm')

        return view

    @property
    def view(self):
        view = self.container_view(self.topology, self.TYPES[self.view_idx])
        self.view_idx += 1
        self.view_idx = self.view_idx % len(self.TYPES)
        return view


def create_topology(topology_json):
    """
    Helper, recursively generate a vCenter topology from a JSON description.
    Return a `MockedMOR` object.

    Examples:
      ```
      topology_desc = "
        {
          "childEntity": [
            {
              "hostFolder": {
                "childEntity": [
                  {
                    "spec": "ClusterComputeResource",
                    "name": "compute_resource1"
                  }
                ]
              },
              "spec": "Datacenter",
              "name": "datacenter1"
            }
          ],
          "spec": "Folder",
          "name": "rootFolder"
        }
      "

      topo = create_topology(topology_desc)

      assert isinstance(topo, Folder)
      assert isinstance(topo.childEntity[0].name) == "compute_resource1"
      ```
    """
    def rec_build(topology_desc):
        """
        Build MORs recursively.
        """
        parsed_topology = {}

        for field, value in topology_desc.iteritems():
            parsed_value = value
            if isinstance(value, dict):
                parsed_value = rec_build(value)
            elif isinstance(value, list):
                parsed_value = [rec_build(obj) for obj in value]
            else:
                parsed_value = value
            parsed_topology[field] = parsed_value

        mor = MockedMOR(**parsed_topology)

        # set parent
        for field, value in topology_desc.iteritems():
            if isinstance(parsed_topology[field], list):
                for m in parsed_topology[field]:
                    if isinstance(m, MockedMOR):
                        m.parent = mor
            elif isinstance(parsed_topology[field], MockedMOR):
                parsed_topology[field].parent = mor

        return mor

    with open(os.path.join(HERE, 'fixtures', topology_json)) as f:
        return rec_build(json.loads(f.read()))


def assertMOR(check, instance, name=None, spec=None, tags=None, count=None, subset=False):
    """
    Helper, assertion on vCenter Manage Object References.
    """
    instance_name = instance['name']
    candidates = []

    if spec:
        mor_list = check.morlist_raw[instance_name][spec]
    else:
        mor_list = [mor for _, mors in check.morlist_raw[instance_name].iteritems() for mor in mors]

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
    check.pool_started = True  # otherwise the mock will be overwritten
    return check


def get_mocked_server():
    """
    Return a mocked Server object
    """
    # create topology from a fixture file
    vcenter_topology = create_topology('vsphere_topology.json')
    # mock pyvmomi stuff
    view_mock = MockedContainer(topology=vcenter_topology)
    viewmanager_mock = MagicMock(**{'CreateContainerView.return_value': view_mock})
    event_mock = MagicMock(createdTime=datetime.now())
    eventmanager_mock = MagicMock(latestEvent=event_mock)
    content_mock = MagicMock(viewManager=viewmanager_mock, eventManager=eventmanager_mock)
    # assemble the mocked server
    server_mock = MagicMock()
    server_mock.configure_mock(**{
        'RetrieveContent.return_value': content_mock,
        'content': content_mock,
    })
    return server_mock
