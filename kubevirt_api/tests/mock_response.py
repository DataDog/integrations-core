# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

GET_VMS_RESPONSE = {
    "apiVersion": "kubevirt.io/v1",
    "items": [
        {
            "apiVersion": "kubevirt.io/v1",
            "kind": "VirtualMachine",
            "metadata": {
                "annotations": {
                    "kubectl.kubernetes.io/last-applied-configuration": '{"apiVersion":"kubevirt.io/v1","kind":"VirtualMachine","metadata":{"annotations":{},"name":"testvm","namespace":"default"},"spec":{"running":false,"template":{"metadata":{"labels":{"kubevirt.io/domain":"testvm","kubevirt.io/size":"small"}},"spec":{"domain":{"devices":{"disks":[{"disk":{"bus":"virtio"},"name":"containerdisk"},{"disk":{"bus":"virtio"},"name":"cloudinitdisk"}],"interfaces":[{"masquerade":{},"name":"default"}]},"resources":{"requests":{"memory":"64M"}}},"networks":[{"name":"default","pod":{}}],"volumes":[{"containerDisk":{"image":"quay.io/kubevirt/cirros-container-disk-demo"},"name":"containerdisk"},{"cloudInitNoCloud":{"userDataBase64":"SGkuXG4="},"name":"cloudinitdisk"}]}}}}\n',  # noqa: E501
                    "kubevirt.io/latest-observed-api-version": "v1",
                    "kubevirt.io/storage-observed-api-version": "v1",
                },
                "creationTimestamp": "2024-07-23T13:30:34Z",
                "finalizers": ["kubevirt.io/virtualMachineControllerFinalize"],
                "generation": 2,
                "managedFields": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:metadata": {
                                "f:annotations": {".": {}, "f:kubectl.kubernetes.io/last-applied-configuration": {}}
                            },
                            "f:spec": {
                                ".": {},
                                "f:template": {
                                    ".": {},
                                    "f:metadata": {
                                        ".": {},
                                        "f:labels": {".": {}, "f:kubevirt.io/domain": {}, "f:kubevirt.io/size": {}},
                                    },
                                    "f:spec": {
                                        ".": {},
                                        "f:domain": {
                                            ".": {},
                                            "f:devices": {".": {}, "f:disks": {}, "f:interfaces": {}},
                                            "f:resources": {".": {}, "f:requests": {".": {}, "f:memory": {}}},
                                        },
                                        "f:networks": {},
                                        "f:volumes": {},
                                    },
                                },
                            },
                        },
                        "manager": "kubectl-client-side-apply",
                        "operation": "Update",
                        "time": "2024-07-23T13:30:34Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {"f:spec": {"f:running": {}}},
                        "manager": "kubectl-patch",
                        "operation": "Update",
                        "time": "2024-07-23T13:30:34Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:metadata": {
                                "f:annotations": {
                                    "f:kubevirt.io/latest-observed-api-version": {},
                                    "f:kubevirt.io/storage-observed-api-version": {},
                                },
                                "f:finalizers": {".": {}, 'v:"kubevirt.io/virtualMachineControllerFinalize"': {}},
                            }
                        },
                        "manager": "virt-controller",
                        "operation": "Update",
                        "time": "2024-07-23T13:30:34Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:status": {
                                ".": {},
                                "f:conditions": {},
                                "f:created": {},
                                "f:desiredGeneration": {},
                                "f:observedGeneration": {},
                                "f:printableStatus": {},
                                "f:ready": {},
                                "f:runStrategy": {},
                                "f:volumeSnapshotStatuses": {},
                            }
                        },
                        "manager": "virt-controller",
                        "operation": "Update",
                        "subresource": "status",
                        "time": "2024-07-23T13:30:51Z",
                    },
                ],
                "name": "testvm",
                "namespace": "default",
                "resourceVersion": "1216",
                "uid": "46bc4e2b-d287-4408-8393-c7accdd73291",
            },
            "spec": {
                "running": True,
                "template": {
                    "metadata": {
                        "creationTimestamp": None,
                        "labels": {"kubevirt.io/domain": "testvm", "kubevirt.io/size": "small"},
                    },
                    "spec": {
                        "architecture": "amd64",
                        "domain": {
                            "devices": {
                                "disks": [
                                    {"disk": {"bus": "virtio"}, "name": "containerdisk"},
                                    {"disk": {"bus": "virtio"}, "name": "cloudinitdisk"},
                                ],
                                "interfaces": [{"masquerade": {}, "name": "default"}],
                            },
                            "machine": {"type": "q35"},
                            "resources": {"requests": {"memory": "64M"}},
                        },
                        "networks": [{"name": "default", "pod": {}}],
                        "volumes": [
                            {
                                "containerDisk": {"image": "quay.io/kubevirt/cirros-container-disk-demo"},
                                "name": "containerdisk",
                            },
                            {"cloudInitNoCloud": {"userDataBase64": "SGkuXG4="}, "name": "cloudinitdisk"},
                        ],
                    },
                },
            },
            "status": {
                "conditions": [
                    {
                        "lastProbeTime": None,
                        "lastTransitionTime": "2024-07-23T13:30:50Z",
                        "status": "True",
                        "type": "Ready",
                    },
                    {"lastProbeTime": None, "lastTransitionTime": None, "status": "True", "type": "LiveMigratable"},
                ],
                "created": True,
                "desiredGeneration": 2,
                "observedGeneration": 2,
                "printableStatus": "Running",
                "ready": True,
                "runStrategy": "Always",
                "volumeSnapshotStatuses": [
                    {
                        "enabled": False,
                        "name": "containerdisk",
                        "reason": "Snapshot is not supported for this volumeSource type [containerdisk]",
                    },
                    {
                        "enabled": False,
                        "name": "cloudinitdisk",
                        "reason": "Snapshot is not supported for this volumeSource type [cloudinitdisk]",
                    },
                ],
            },
        },
        {
            "apiVersion": "kubevirt.io/v1",
            "kind": "VirtualMachine",
            "metadata": {
                "annotations": {
                    "kubectl.kubernetes.io/last-applied-configuration": '{"apiVersion":"kubevirt.io/v1","kind":"VirtualMachine","metadata":{"annotations":{},"name":"testvm-2","namespace":"default"},"spec":{"running":false,"template":{"metadata":{"labels":{"kubevirt.io/domain":"testvm","kubevirt.io/size":"small"}},"spec":{"domain":{"devices":{"disks":[{"disk":{"bus":"virtio"},"name":"containerdisk"},{"disk":{"bus":"virtio"},"name":"cloudinitdisk"}],"interfaces":[{"masquerade":{},"name":"default"}]},"resources":{"requests":{"memory":"64M"}}},"networks":[{"name":"default","pod":{}}],"volumes":[{"containerDisk":{"image":"quay.io/kubevirt/cirros-container-disk-demo"},"name":"containerdisk"},{"cloudInitNoCloud":{"userDataBase64":"SGkuXG4="},"name":"cloudinitdisk"}]}}}}\n',  # noqa: E501
                    "kubevirt.io/latest-observed-api-version": "v1",
                    "kubevirt.io/storage-observed-api-version": "v1",
                },
                "creationTimestamp": "2024-07-24T13:18:36Z",
                "finalizers": ["kubevirt.io/virtualMachineControllerFinalize"],
                "generation": 2,
                "managedFields": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:metadata": {
                                "f:annotations": {".": {}, "f:kubectl.kubernetes.io/last-applied-configuration": {}}
                            },
                            "f:spec": {
                                ".": {},
                                "f:template": {
                                    ".": {},
                                    "f:metadata": {
                                        ".": {},
                                        "f:labels": {".": {}, "f:kubevirt.io/domain": {}, "f:kubevirt.io/size": {}},
                                    },
                                    "f:spec": {
                                        ".": {},
                                        "f:domain": {
                                            ".": {},
                                            "f:devices": {".": {}, "f:disks": {}, "f:interfaces": {}},
                                            "f:resources": {".": {}, "f:requests": {".": {}, "f:memory": {}}},
                                        },
                                        "f:networks": {},
                                        "f:volumes": {},
                                    },
                                },
                            },
                        },
                        "manager": "kubectl-client-side-apply",
                        "operation": "Update",
                        "time": "2024-07-24T13:18:36Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:metadata": {
                                "f:annotations": {
                                    "f:kubevirt.io/latest-observed-api-version": {},
                                    "f:kubevirt.io/storage-observed-api-version": {},
                                },
                                "f:finalizers": {".": {}, 'v:"kubevirt.io/virtualMachineControllerFinalize"': {}},
                            }
                        },
                        "manager": "virt-controller",
                        "operation": "Update",
                        "time": "2024-07-24T13:18:36Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {"f:spec": {"f:running": {}}},
                        "manager": "kubectl-patch",
                        "operation": "Update",
                        "time": "2024-07-24T13:18:55Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:status": {
                                ".": {},
                                "f:conditions": {},
                                "f:created": {},
                                "f:desiredGeneration": {},
                                "f:observedGeneration": {},
                                "f:printableStatus": {},
                                "f:ready": {},
                                "f:runStrategy": {},
                                "f:volumeSnapshotStatuses": {},
                            }
                        },
                        "manager": "virt-controller",
                        "operation": "Update",
                        "subresource": "status",
                        "time": "2024-07-24T13:19:13Z",
                    },
                ],
                "name": "testvm-2",
                "namespace": "default",
                "resourceVersion": "284129",
                "uid": "2afae6da-dcdd-4749-a198-c48877b22662",
            },
            "spec": {
                "running": True,
                "template": {
                    "metadata": {
                        "creationTimestamp": None,
                        "labels": {"kubevirt.io/domain": "testvm", "kubevirt.io/size": "small"},
                    },
                    "spec": {
                        "architecture": "amd64",
                        "domain": {
                            "devices": {
                                "disks": [
                                    {"disk": {"bus": "virtio"}, "name": "containerdisk"},
                                    {"disk": {"bus": "virtio"}, "name": "cloudinitdisk"},
                                ],
                                "interfaces": [{"masquerade": {}, "name": "default"}],
                            },
                            "machine": {"type": "q35"},
                            "resources": {"requests": {"memory": "64M"}},
                        },
                        "networks": [{"name": "default", "pod": {}}],
                        "volumes": [
                            {
                                "containerDisk": {"image": "quay.io/kubevirt/cirros-container-disk-demo"},
                                "name": "containerdisk",
                            },
                            {"cloudInitNoCloud": {"userDataBase64": "SGkuXG4="}, "name": "cloudinitdisk"},
                        ],
                    },
                },
            },
            "status": {
                "conditions": [
                    {
                        "lastProbeTime": None,
                        "lastTransitionTime": "2024-07-24T13:19:12Z",
                        "status": "True",
                        "type": "Ready",
                    },
                    {"lastProbeTime": None, "lastTransitionTime": None, "status": "True", "type": "LiveMigratable"},
                ],
                "created": True,
                "desiredGeneration": 2,
                "observedGeneration": 2,
                "printableStatus": "Running",
                "ready": True,
                "runStrategy": "Always",
                "volumeSnapshotStatuses": [
                    {
                        "enabled": False,
                        "name": "containerdisk",
                        "reason": "Snapshot is not supported for this volumeSource type [containerdisk]",
                    },
                    {
                        "enabled": False,
                        "name": "cloudinitdisk",
                        "reason": "Snapshot is not supported for this volumeSource type [cloudinitdisk]",
                    },
                ],
            },
        },
    ],
    "kind": "VirtualMachineList",
    "metadata": {"continue": "", "resourceVersion": "1246681"},
}

GET_VMIS_RESPONSE = {
    "apiVersion": "kubevirt.io/v1",
    "items": [
        {
            "apiVersion": "kubevirt.io/v1",
            "kind": "VirtualMachineInstance",
            "metadata": {
                "annotations": {
                    "kubevirt.io/latest-observed-api-version": "v1",
                    "kubevirt.io/storage-observed-api-version": "v1",
                    "kubevirt.io/vm-generation": "2",
                },
                "creationTimestamp": "2024-07-23T13:30:34Z",
                "finalizers": ["kubevirt.io/virtualMachineControllerFinalize", "foregroundDeleteVirtualMachine"],
                "generation": 10,
                "labels": {
                    "kubevirt.io/domain": "testvm",
                    "kubevirt.io/nodeName": "dev-kubevirt-control-plane",
                    "kubevirt.io/size": "small",
                    "random-prefix/foo": "bar",
                    "random-prefix/baz": "biz",
                },
                "managedFields": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:metadata": {
                                "f:annotations": {
                                    ".": {},
                                    "f:kubevirt.io/latest-observed-api-version": {},
                                    "f:kubevirt.io/storage-observed-api-version": {},
                                    "f:kubevirt.io/vm-generation": {},
                                },
                                "f:finalizers": {".": {}, 'v:"kubevirt.io/virtualMachineControllerFinalize"': {}},
                                "f:labels": {
                                    ".": {},
                                    "f:kubevirt.io/domain": {},
                                    "f:kubevirt.io/nodeName": {},
                                    "f:kubevirt.io/size": {},
                                },
                                "f:ownerReferences": {".": {}, 'k:{"uid":"46bc4e2b-d287-4408-8393-c7accdd73291"}': {}},
                            },
                            "f:spec": {
                                ".": {},
                                "f:architecture": {},
                                "f:domain": {
                                    ".": {},
                                    "f:devices": {".": {}, "f:disks": {}, "f:interfaces": {}},
                                    "f:firmware": {".": {}, "f:uuid": {}},
                                    "f:machine": {".": {}, "f:type": {}},
                                    "f:resources": {".": {}, "f:requests": {".": {}, "f:memory": {}}},
                                },
                                "f:networks": {},
                                "f:volumes": {},
                            },
                            "f:status": {
                                ".": {},
                                "f:activePods": {".": {}, "f:d75f9344-5f21-4dc5-8698-3eba155eb9e2": {}},
                                "f:conditions": {},
                                "f:currentCPUTopology": {".": {}, "f:cores": {}, "f:sockets": {}, "f:threads": {}},
                                "f:guestOSInfo": {},
                                "f:launcherContainerImageVersion": {},
                                "f:migrationTransport": {},
                                "f:nodeName": {},
                                "f:qosClass": {},
                                "f:runtimeUser": {},
                                "f:virtualMachineRevisionName": {},
                            },
                        },
                        "manager": "virt-controller",
                        "operation": "Update",
                        "time": "2024-07-23T13:30:51Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:status": {
                                "f:interfaces": {},
                                "f:machine": {".": {}, "f:type": {}},
                                "f:memory": {".": {}, "f:guestCurrent": {}},
                                "f:migrationMethod": {},
                                "f:phase": {},
                                "f:phaseTransitionTimestamps": {},
                                "f:selinuxContext": {},
                                "f:volumeStatus": {},
                            }
                        },
                        "manager": "virt-handler",
                        "operation": "Update",
                        "time": "2024-07-23T13:34:52Z",
                    },
                ],
                "name": "testvm",
                "namespace": "default",
                "ownerReferences": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "blockOwnerDeletion": True,
                        "controller": True,
                        "kind": "VirtualMachine",
                        "name": "testvm",
                        "uid": "46bc4e2b-d287-4408-8393-c7accdd73291",
                    }
                ],
                "resourceVersion": "2013",
                "uid": "0e611e1b-e538-44bb-b8a7-60351c19718a",
            },
            "spec": {
                "architecture": "amd64",
                "domain": {
                    "cpu": {"cores": 1, "model": "host-model", "sockets": 1, "threads": 1},
                    "devices": {
                        "disks": [
                            {"disk": {"bus": "virtio"}, "name": "containerdisk"},
                            {"disk": {"bus": "virtio"}, "name": "cloudinitdisk"},
                        ],
                        "interfaces": [{"masquerade": {}, "name": "default"}],
                    },
                    "features": {"acpi": {"enabled": True}},
                    "firmware": {"uuid": "5a9fc181-957e-5c32-9e5a-2de5e9673531"},
                    "machine": {"type": "q35"},
                    "resources": {"requests": {"memory": "64M"}},
                },
                "evictionStrategy": "None",
                "networks": [{"name": "default", "pod": {}}],
                "volumes": [
                    {
                        "containerDisk": {
                            "image": "quay.io/kubevirt/cirros-container-disk-demo",
                            "imagePullPolicy": "Always",
                        },
                        "name": "containerdisk",
                    },
                    {"cloudInitNoCloud": {"userDataBase64": "SGkuXG4="}, "name": "cloudinitdisk"},
                ],
            },
            "status": {
                "activePods": {"d75f9344-5f21-4dc5-8698-3eba155eb9e2": "dev-kubevirt-control-plane"},
                "conditions": [
                    {
                        "lastProbeTime": None,
                        "lastTransitionTime": "2024-07-23T13:30:50Z",
                        "status": "True",
                        "type": "Ready",
                    },
                    {"lastProbeTime": None, "lastTransitionTime": None, "status": "True", "type": "LiveMigratable"},
                ],
                "currentCPUTopology": {"cores": 1, "sockets": 1, "threads": 1},
                "guestOSInfo": {},
                "interfaces": [
                    {
                        "infoSource": "domain",
                        "ipAddress": "10.244.0.12",
                        "ipAddresses": ["10.244.0.12"],
                        "mac": "02:5c:f5:c6:e8:e8",
                        "name": "default",
                        "queueCount": 1,
                    }
                ],
                "launcherContainerImageVersion": "quay.io/kubevirt/virt-launcher:v1.2.2",
                "machine": {"type": "pc-q35-rhel9.2.0"},
                "memory": {"guestCurrent": "62500Ki"},
                "migrationMethod": "BlockMigration",
                "migrationTransport": "Unix",
                "nodeName": "dev-kubevirt-control-plane",
                "phase": "Running",
                "phaseTransitionTimestamps": [
                    {"phase": "Pending", "phaseTransitionTimestamp": "2024-07-23T13:30:34Z"},
                    {"phase": "Scheduling", "phaseTransitionTimestamp": "2024-07-23T13:30:34Z"},
                    {"phase": "Scheduled", "phaseTransitionTimestamp": "2024-07-23T13:30:50Z"},
                    {"phase": "Running", "phaseTransitionTimestamp": "2024-07-23T13:30:51Z"},
                ],
                "qosClass": "Burstable",
                "runtimeUser": 107,
                "selinuxContext": "none",
                "virtualMachineRevisionName": "revision-start-vm-46bc4e2b-d287-4408-8393-c7accdd73291-2",
                "volumeStatus": [
                    {"name": "cloudinitdisk", "size": 1048576, "target": "vdb"},
                    {"containerDiskVolume": {"checksum": 101079325}, "name": "containerdisk", "target": "vda"},
                ],
            },
        },
        {
            "apiVersion": "kubevirt.io/v1",
            "kind": "VirtualMachineInstance",
            "metadata": {
                "annotations": {
                    "kubevirt.io/latest-observed-api-version": "v1",
                    "kubevirt.io/storage-observed-api-version": "v1",
                    "kubevirt.io/vm-generation": "2",
                },
                "creationTimestamp": "2024-07-24T13:18:55Z",
                "finalizers": ["kubevirt.io/virtualMachineControllerFinalize", "foregroundDeleteVirtualMachine"],
                "generation": 10,
                "labels": {
                    "kubevirt.io/domain": "testvm",
                    "kubevirt.io/nodeName": "dev-kubevirt-control-plane",
                    "kubevirt.io/size": "small",
                },
                "managedFields": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:metadata": {
                                "f:annotations": {
                                    ".": {},
                                    "f:kubevirt.io/latest-observed-api-version": {},
                                    "f:kubevirt.io/storage-observed-api-version": {},
                                    "f:kubevirt.io/vm-generation": {},
                                },
                                "f:finalizers": {".": {}, 'v:"kubevirt.io/virtualMachineControllerFinalize"': {}},
                                "f:labels": {
                                    ".": {},
                                    "f:kubevirt.io/domain": {},
                                    "f:kubevirt.io/nodeName": {},
                                    "f:kubevirt.io/size": {},
                                },
                                "f:ownerReferences": {".": {}, 'k:{"uid":"2afae6da-dcdd-4749-a198-c48877b22662"}': {}},
                            },
                            "f:spec": {
                                ".": {},
                                "f:architecture": {},
                                "f:domain": {
                                    ".": {},
                                    "f:devices": {".": {}, "f:disks": {}, "f:interfaces": {}},
                                    "f:firmware": {".": {}, "f:uuid": {}},
                                    "f:machine": {".": {}, "f:type": {}},
                                    "f:resources": {".": {}, "f:requests": {".": {}, "f:memory": {}}},
                                },
                                "f:networks": {},
                                "f:volumes": {},
                            },
                            "f:status": {
                                ".": {},
                                "f:activePods": {".": {}, "f:f4a198d9-0efb-486a-adfc-05f0757518da": {}},
                                "f:conditions": {},
                                "f:currentCPUTopology": {".": {}, "f:cores": {}, "f:sockets": {}, "f:threads": {}},
                                "f:guestOSInfo": {},
                                "f:launcherContainerImageVersion": {},
                                "f:migrationTransport": {},
                                "f:nodeName": {},
                                "f:qosClass": {},
                                "f:runtimeUser": {},
                                "f:virtualMachineRevisionName": {},
                            },
                        },
                        "manager": "virt-controller",
                        "operation": "Update",
                        "time": "2024-07-24T13:19:13Z",
                    },
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "fieldsType": "FieldsV1",
                        "fieldsV1": {
                            "f:status": {
                                "f:interfaces": {},
                                "f:machine": {".": {}, "f:type": {}},
                                "f:memory": {".": {}, "f:guestCurrent": {}},
                                "f:migrationMethod": {},
                                "f:phase": {},
                                "f:phaseTransitionTimestamps": {},
                                "f:selinuxContext": {},
                                "f:volumeStatus": {},
                            }
                        },
                        "manager": "virt-handler",
                        "operation": "Update",
                        "time": "2024-07-24T13:19:52Z",
                    },
                ],
                "name": "testvm-2",
                "namespace": "default",
                "ownerReferences": [
                    {
                        "apiVersion": "kubevirt.io/v1",
                        "blockOwnerDeletion": True,
                        "controller": True,
                        "kind": "VirtualMachine",
                        "name": "testvm-2",
                        "uid": "2afae6da-dcdd-4749-a198-c48877b22662",
                    }
                ],
                "resourceVersion": "284259",
                "uid": "f1f3ae4b-f81f-406f-a574-f12e7e3ba4f2",
            },
            "spec": {
                "architecture": "amd64",
                "domain": {
                    "cpu": {"cores": 1, "model": "host-model", "sockets": 1, "threads": 1},
                    "devices": {
                        "disks": [
                            {"disk": {"bus": "virtio"}, "name": "containerdisk"},
                            {"disk": {"bus": "virtio"}, "name": "cloudinitdisk"},
                        ],
                        "interfaces": [{"masquerade": {}, "name": "default"}],
                    },
                    "features": {"acpi": {"enabled": True}},
                    "firmware": {"uuid": "0e44be5a-ff12-52fb-9413-07b52f3593c3"},
                    "machine": {"type": "q35"},
                    "resources": {"requests": {"memory": "64M"}},
                },
                "evictionStrategy": "None",
                "networks": [{"name": "default", "pod": {}}],
                "volumes": [
                    {
                        "containerDisk": {
                            "image": "quay.io/kubevirt/cirros-container-disk-demo",
                            "imagePullPolicy": "Always",
                        },
                        "name": "containerdisk",
                    },
                    {"cloudInitNoCloud": {"userDataBase64": "SGkuXG4="}, "name": "cloudinitdisk"},
                ],
            },
            "status": {
                "activePods": {"f4a198d9-0efb-486a-adfc-05f0757518da": "dev-kubevirt-control-plane"},
                "conditions": [
                    {
                        "lastProbeTime": None,
                        "lastTransitionTime": "2024-07-24T13:19:12Z",
                        "status": "True",
                        "type": "Ready",
                    },
                    {"lastProbeTime": None, "lastTransitionTime": None, "status": "True", "type": "LiveMigratable"},
                ],
                "currentCPUTopology": {"cores": 1, "sockets": 1, "threads": 1},
                "guestOSInfo": {},
                "interfaces": [
                    {
                        "infoSource": "domain",
                        "ipAddress": "10.244.0.17",
                        "ipAddresses": ["10.244.0.17"],
                        "mac": "f2:f1:c6:fe:96:c7",
                        "name": "default",
                        "queueCount": 1,
                    }
                ],
                "launcherContainerImageVersion": "quay.io/kubevirt/virt-launcher:v1.2.2",
                "machine": {"type": "pc-q35-rhel9.2.0"},
                "memory": {"guestCurrent": "62500Ki"},
                "migrationMethod": "BlockMigration",
                "migrationTransport": "Unix",
                "nodeName": "dev-kubevirt-control-plane",
                "phase": "Running",
                "phaseTransitionTimestamps": [
                    {"phase": "Pending", "phaseTransitionTimestamp": "2024-07-24T13:18:55Z"},
                    {"phase": "Scheduling", "phaseTransitionTimestamp": "2024-07-24T13:18:55Z"},
                    {"phase": "Scheduled", "phaseTransitionTimestamp": "2024-07-24T13:19:12Z"},
                    {"phase": "Running", "phaseTransitionTimestamp": "2024-07-24T13:19:13Z"},
                ],
                "qosClass": "Burstable",
                "runtimeUser": 107,
                "selinuxContext": "none",
                "virtualMachineRevisionName": "revision-start-vm-2afae6da-dcdd-4749-a198-c48877b22662-2",
                "volumeStatus": [
                    {"name": "cloudinitdisk", "size": 1048576, "target": "vdb"},
                    {"containerDiskVolume": {"checksum": 101079325}, "name": "containerdisk", "target": "vda"},
                ],
            },
        },
    ],
    "kind": "VirtualMachineInstanceList",
    "metadata": {"continue": "", "resourceVersion": "1236015"},
}
