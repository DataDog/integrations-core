# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime

from dateutil.tz import tzutc
from kubernetes.client.models import V1ObjectMeta, V1Pod

annotations = {
    "kubevirt.io/install-strategy-identifier": "96d0fd48fa88abe041085474347e87222b076258",
    "kubevirt.io/install-strategy-registry": "quay.io/kubevirt",
    "kubevirt.io/install-strategy-version": "v1.3.0",
}

labels = {
    "app.kubernetes.io/component": "kubevirt",
    "app.kubernetes.io/managed-by": "virt-operator",
    "app.kubernetes.io/version": "v1.3.0",
    "kubevirt.io": "virt-api",
    "pod-template-hash": "7976d99767",
    "prometheus.kubevirt.io": "true",
}

metadata = V1ObjectMeta(
    name="virt-api-7976d99767-cbj7g",
    namespace="kubevirt",
    annotations=annotations,
    labels=labels,
    uid="b2d68e35-47a1-43aa-a4fa-3b15d63e2a66",
)

GET_PODS_RESPONSE_VIRT_API_POD = [
    V1Pod(
        metadata=metadata,
        **{
            "api_version": None,
            "kind": None,
            "spec": {
                "active_deadline_seconds": None,
                "affinity": {
                    "node_affinity": {
                        "preferred_during_scheduling_ignored_during_execution": [
                            {
                                "preference": {
                                    "match_expressions": [
                                        {
                                            "key": "node-role.kubernetes.io/worker",
                                            "operator": "DoesNotExist",
                                            "values": None,
                                        }
                                    ],
                                    "match_fields": None,
                                },
                                "weight": 100,
                            }
                        ],
                        "required_during_scheduling_ignored_during_execution": {
                            "node_selector_terms": [
                                {
                                    "match_expressions": [
                                        {
                                            "key": "node-role.kubernetes.io/control-plane",
                                            "operator": "Exists",
                                            "values": None,
                                        }
                                    ],
                                    "match_fields": None,
                                },
                                {
                                    "match_expressions": [
                                        {"key": "node-role.kubernetes.io/master", "operator": "Exists", "values": None}
                                    ],
                                    "match_fields": None,
                                },
                            ]
                        },
                    },
                    "pod_affinity": None,
                    "pod_anti_affinity": {
                        "preferred_during_scheduling_ignored_during_execution": [
                            {
                                "pod_affinity_term": {
                                    "label_selector": {
                                        "match_expressions": [
                                            {"key": "kubevirt.io", "operator": "In", "values": ["virt-api"]}
                                        ],
                                        "match_labels": None,
                                    },
                                    "match_label_keys": None,
                                    "mismatch_label_keys": None,
                                    "namespace_selector": None,
                                    "namespaces": None,
                                    "topology_key": "kubernetes.io/hostname",
                                },
                                "weight": 1,
                            }
                        ],
                        "required_during_scheduling_ignored_during_execution": None,
                    },
                },
                "automount_service_account_token": None,
                "containers": [
                    {
                        "args": ["--port", "8443", "--console-server-port", "8186", "--subresources-only", "-v", "2"],
                        "command": ["virt-api"],
                        "env": None,
                        "env_from": None,
                        "image": "quay.io/kubevirt/virt-api:v1.3.0",
                        "image_pull_policy": "IfNotPresent",
                        "lifecycle": None,
                        "liveness_probe": None,
                        "name": "virt-api",
                        "ports": [
                            {
                                "container_port": 8443,
                                "host_ip": None,
                                "host_port": None,
                                "name": "virt-api",
                                "protocol": "TCP",
                            },
                            {
                                "container_port": 8443,
                                "host_ip": None,
                                "host_port": None,
                                "name": "metrics",
                                "protocol": "TCP",
                            },
                        ],
                        "readiness_probe": {
                            "_exec": None,
                            "failure_threshold": 3,
                            "grpc": None,
                            "http_get": {
                                "host": None,
                                "http_headers": None,
                                "path": "/apis/subresources.kubevirt.io/v1/healthz",
                                "port": 8443,
                                "scheme": "HTTPS",
                            },
                            "initial_delay_seconds": 15,
                            "period_seconds": 10,
                            "success_threshold": 1,
                            "tcp_socket": None,
                            "termination_grace_period_seconds": None,
                            "timeout_seconds": 1,
                        },
                        "resize_policy": None,
                        "resources": {"claims": None, "limits": None, "requests": {"cpu": "5m", "memory": "500Mi"}},
                        "restart_policy": None,
                        "security_context": {
                            "allow_privilege_escalation": False,
                            "app_armor_profile": None,
                            "capabilities": {"add": None, "drop": ["ALL"]},
                            "privileged": None,
                            "proc_mount": None,
                            "read_only_root_filesystem": None,
                            "run_as_group": None,
                            "run_as_non_root": None,
                            "run_as_user": None,
                            "se_linux_options": None,
                            "seccomp_profile": {"localhost_profile": None, "type": "RuntimeDefault"},
                            "windows_options": None,
                        },
                        "startup_probe": None,
                        "stdin": None,
                        "stdin_once": None,
                        "termination_message_path": "/dev/termination-log",
                        "termination_message_policy": "File",
                        "tty": None,
                        "volume_devices": None,
                        "volume_mounts": [
                            {
                                "mount_path": "/etc/virt-api/certificates",
                                "mount_propagation": None,
                                "name": "kubevirt-virt-api-certs",
                                "read_only": True,
                                "recursive_read_only": None,
                                "sub_path": None,
                                "sub_path_expr": None,
                            },
                            {
                                "mount_path": "/etc/virt-handler/clientcertificates",
                                "mount_propagation": None,
                                "name": "kubevirt-virt-handler-certs",
                                "read_only": True,
                                "recursive_read_only": None,
                                "sub_path": None,
                                "sub_path_expr": None,
                            },
                            {
                                "mount_path": "/profile-data",
                                "mount_propagation": None,
                                "name": "profile-data",
                                "read_only": None,
                                "recursive_read_only": None,
                                "sub_path": None,
                                "sub_path_expr": None,
                            },
                            {
                                "mount_path": "/var/run/secrets/kubernetes.io/serviceaccount",
                                "mount_propagation": None,
                                "name": "kube-api-access-vht47",
                                "read_only": True,
                                "recursive_read_only": None,
                                "sub_path": None,
                                "sub_path_expr": None,
                            },
                        ],
                        "working_dir": None,
                    }
                ],
                "dns_config": None,
                "dns_policy": "ClusterFirst",
                "enable_service_links": True,
                "ephemeral_containers": None,
                "host_aliases": None,
                "host_ipc": None,
                "host_network": None,
                "host_pid": None,
                "host_users": None,
                "hostname": None,
                "image_pull_secrets": None,
                "init_containers": None,
                "node_name": "minikube",
                "node_selector": {"kubernetes.io/os": "linux"},
                "os": None,
                "overhead": None,
                "preemption_policy": "PreemptLowerPriority",
                "priority": 1000000000,
                "priority_class_name": "kubevirt-cluster-critical",
                "readiness_gates": None,
                "resource_claims": None,
                "restart_policy": "Always",
                "runtime_class_name": None,
                "scheduler_name": "default-scheduler",
                "scheduling_gates": None,
                "security_context": {
                    "app_armor_profile": None,
                    "fs_group": None,
                    "fs_group_change_policy": None,
                    "run_as_group": None,
                    "run_as_non_root": True,
                    "run_as_user": None,
                    "se_linux_options": None,
                    "seccomp_profile": {"localhost_profile": None, "type": "RuntimeDefault"},
                    "supplemental_groups": None,
                    "sysctls": None,
                    "windows_options": None,
                },
                "service_account": "kubevirt-apiserver",
                "service_account_name": "kubevirt-apiserver",
                "set_hostname_as_fqdn": None,
                "share_process_namespace": None,
                "subdomain": None,
                "termination_grace_period_seconds": 30,
                "tolerations": [
                    {
                        "effect": None,
                        "key": "CriticalAddonsOnly",
                        "operator": "Exists",
                        "toleration_seconds": None,
                        "value": None,
                    },
                    {
                        "effect": "NoSchedule",
                        "key": "node-role.kubernetes.io/control-plane",
                        "operator": "Exists",
                        "toleration_seconds": None,
                        "value": None,
                    },
                    {
                        "effect": "NoSchedule",
                        "key": "node-role.kubernetes.io/master",
                        "operator": "Exists",
                        "toleration_seconds": None,
                        "value": None,
                    },
                    {
                        "effect": "NoExecute",
                        "key": "node.kubernetes.io/not-ready",
                        "operator": "Exists",
                        "toleration_seconds": 300,
                        "value": None,
                    },
                    {
                        "effect": "NoExecute",
                        "key": "node.kubernetes.io/unreachable",
                        "operator": "Exists",
                        "toleration_seconds": 300,
                        "value": None,
                    },
                ],
                "topology_spread_constraints": None,
                "volumes": [
                    {
                        "aws_elastic_block_store": None,
                        "azure_disk": None,
                        "azure_file": None,
                        "cephfs": None,
                        "cinder": None,
                        "config_map": None,
                        "csi": None,
                        "downward_api": None,
                        "empty_dir": None,
                        "ephemeral": None,
                        "fc": None,
                        "flex_volume": None,
                        "flocker": None,
                        "gce_persistent_disk": None,
                        "git_repo": None,
                        "glusterfs": None,
                        "host_path": None,
                        "iscsi": None,
                        "name": "kubevirt-virt-api-certs",
                        "nfs": None,
                        "persistent_volume_claim": None,
                        "photon_persistent_disk": None,
                        "portworx_volume": None,
                        "projected": None,
                        "quobyte": None,
                        "rbd": None,
                        "scale_io": None,
                        "secret": {
                            "default_mode": 420,
                            "items": None,
                            "optional": True,
                            "secret_name": "kubevirt-virt-api-certs",
                        },
                        "storageos": None,
                        "vsphere_volume": None,
                    },
                    {
                        "aws_elastic_block_store": None,
                        "azure_disk": None,
                        "azure_file": None,
                        "cephfs": None,
                        "cinder": None,
                        "config_map": None,
                        "csi": None,
                        "downward_api": None,
                        "empty_dir": None,
                        "ephemeral": None,
                        "fc": None,
                        "flex_volume": None,
                        "flocker": None,
                        "gce_persistent_disk": None,
                        "git_repo": None,
                        "glusterfs": None,
                        "host_path": None,
                        "iscsi": None,
                        "name": "kubevirt-virt-handler-certs",
                        "nfs": None,
                        "persistent_volume_claim": None,
                        "photon_persistent_disk": None,
                        "portworx_volume": None,
                        "projected": None,
                        "quobyte": None,
                        "rbd": None,
                        "scale_io": None,
                        "secret": {
                            "default_mode": 420,
                            "items": None,
                            "optional": True,
                            "secret_name": "kubevirt-virt-handler-certs",
                        },
                        "storageos": None,
                        "vsphere_volume": None,
                    },
                    {
                        "aws_elastic_block_store": None,
                        "azure_disk": None,
                        "azure_file": None,
                        "cephfs": None,
                        "cinder": None,
                        "config_map": None,
                        "csi": None,
                        "downward_api": None,
                        "empty_dir": {"medium": None, "size_limit": None},
                        "ephemeral": None,
                        "fc": None,
                        "flex_volume": None,
                        "flocker": None,
                        "gce_persistent_disk": None,
                        "git_repo": None,
                        "glusterfs": None,
                        "host_path": None,
                        "iscsi": None,
                        "name": "profile-data",
                        "nfs": None,
                        "persistent_volume_claim": None,
                        "photon_persistent_disk": None,
                        "portworx_volume": None,
                        "projected": None,
                        "quobyte": None,
                        "rbd": None,
                        "scale_io": None,
                        "secret": None,
                        "storageos": None,
                        "vsphere_volume": None,
                    },
                    {
                        "aws_elastic_block_store": None,
                        "azure_disk": None,
                        "azure_file": None,
                        "cephfs": None,
                        "cinder": None,
                        "config_map": None,
                        "csi": None,
                        "downward_api": None,
                        "empty_dir": None,
                        "ephemeral": None,
                        "fc": None,
                        "flex_volume": None,
                        "flocker": None,
                        "gce_persistent_disk": None,
                        "git_repo": None,
                        "glusterfs": None,
                        "host_path": None,
                        "iscsi": None,
                        "name": "kube-api-access-vht47",
                        "nfs": None,
                        "persistent_volume_claim": None,
                        "photon_persistent_disk": None,
                        "portworx_volume": None,
                        "projected": {
                            "default_mode": 420,
                            "sources": [
                                {
                                    "cluster_trust_bundle": None,
                                    "config_map": None,
                                    "downward_api": None,
                                    "secret": None,
                                    "service_account_token": {
                                        "audience": None,
                                        "expiration_seconds": 3607,
                                        "path": "token",
                                    },
                                },
                                {
                                    "cluster_trust_bundle": None,
                                    "config_map": {
                                        "items": [{"key": "ca.crt", "mode": None, "path": "ca.crt"}],
                                        "name": "kube-root-ca.crt",
                                        "optional": None,
                                    },
                                    "downward_api": None,
                                    "secret": None,
                                    "service_account_token": None,
                                },
                                {
                                    "cluster_trust_bundle": None,
                                    "config_map": None,
                                    "downward_api": {
                                        "items": [
                                            {
                                                "field_ref": {"api_version": "v1", "field_path": "metadata.namespace"},
                                                "mode": None,
                                                "path": "namespace",
                                                "resource_field_ref": None,
                                            }
                                        ]
                                    },
                                    "secret": None,
                                    "service_account_token": None,
                                },
                            ],
                        },
                        "quobyte": None,
                        "rbd": None,
                        "scale_io": None,
                        "secret": None,
                        "storageos": None,
                        "vsphere_volume": None,
                    },
                ],
            },
            "status": {
                "conditions": [
                    {
                        "last_probe_time": None,
                        "last_transition_time": datetime.datetime(2024, 7, 25, 15, 16, 47, tzinfo=tzutc()),
                        "message": None,
                        "reason": None,
                        "status": "True",
                        "type": "PodReadyToStartContainers",
                    },
                    {
                        "last_probe_time": None,
                        "last_transition_time": datetime.datetime(2024, 7, 24, 22, 15, 4, tzinfo=tzutc()),
                        "message": None,
                        "reason": None,
                        "status": "True",
                        "type": "Initialized",
                    },
                    {
                        "last_probe_time": None,
                        "last_transition_time": datetime.datetime(2024, 7, 25, 15, 17, 6, tzinfo=tzutc()),
                        "message": None,
                        "reason": None,
                        "status": "True",
                        "type": "Ready",
                    },
                    {
                        "last_probe_time": None,
                        "last_transition_time": datetime.datetime(2024, 7, 25, 15, 17, 6, tzinfo=tzutc()),
                        "message": None,
                        "reason": None,
                        "status": "True",
                        "type": "ContainersReady",
                    },
                    {
                        "last_probe_time": None,
                        "last_transition_time": datetime.datetime(2024, 7, 24, 22, 15, 4, tzinfo=tzutc()),
                        "message": None,
                        "reason": None,
                        "status": "True",
                        "type": "PodScheduled",
                    },
                ],
                "container_statuses": [
                    {
                        "allocated_resources": None,
                        "container_id": "docker://8ad97c811573006c67ad0aee2734feef886ac99db89b1be0cca4c7ce588b7806",
                        "image": "quay.io/kubevirt/virt-api:v1.3.0",
                        "image_id": "docker-pullable://quay.io/kubevirt/virt-api@sha256:3f1e97424b7563fbab544b128fb06d0b84efea1a209be09178722309f34b215e",
                        "last_state": {
                            "running": None,
                            "terminated": {
                                "container_id": "docker://8160bb0b4f3c0fa947151d958e931d009dd915f3c402ba877fd02ae93e996e9c",
                                "exit_code": 0,
                                "finished_at": datetime.datetime(2024, 7, 25, 14, 32, 13, tzinfo=tzutc()),
                                "message": None,
                                "reason": "Completed",
                                "signal": None,
                                "started_at": datetime.datetime(2024, 7, 24, 22, 15, 9, tzinfo=tzutc()),
                            },
                            "waiting": None,
                        },
                        "name": "virt-api",
                        "ready": True,
                        "resources": None,
                        "restart_count": 1,
                        "started": True,
                        "state": {
                            "running": {"started_at": datetime.datetime(2024, 7, 25, 15, 16, 47, tzinfo=tzutc())},
                            "terminated": None,
                            "waiting": None,
                        },
                        "volume_mounts": None,
                    }
                ],
                "ephemeral_container_statuses": None,
                "host_i_ps": [{"ip": "192.168.49.2"}],
                "host_ip": "192.168.49.2",
                "init_container_statuses": None,
                "message": None,
                "nominated_node_name": None,
                "phase": "Running",
                "pod_i_ps": [{"ip": "10.244.0.38"}],
                "pod_ip": "10.244.0.38",
                "qos_class": "Burstable",
                "reason": None,
                "resize": None,
                "resource_claim_statuses": None,
                "start_time": datetime.datetime(2024, 7, 24, 22, 15, 4, tzinfo=tzutc()),
            },
        },
    )
]


GET_VMS_RESPONSE = [
    {
        "apiVersion": "kubevirt.io/v1",
        "kind": "VirtualMachine",
        "metadata": {
            "annotations": {
                "kubectl.kubernetes.io/last-applied-configuration": '{"apiVersion":"kubevirt.io/v1","kind":"VirtualMachine","metadata":{"annotations":{},"name":"testvm","namespace":"default"},"spec":{"running":false,"template":{"metadata":{"labels":{"kubevirt.io/domain":"testvm","kubevirt.io/size":"small"}},"spec":{"domain":{"devices":{"disks":[{"disk":{"bus":"virtio"},"name":"containerdisk"},{"disk":{"bus":"virtio"},"name":"cloudinitdisk"}],"interfaces":[{"masquerade":{},"name":"default"}]},"resources":{"requests":{"memory":"64M"}}},"networks":[{"name":"default","pod":{}}],"volumes":[{"containerDisk":{"image":"quay.io/kubevirt/cirros-container-disk-demo"},"name":"containerdisk"},{"cloudInitNoCloud":{"userDataBase64":"SGkuXG4="},"name":"cloudinitdisk"}]}}}}\n',  # noqa: E501
                "kubevirt.io/latest-observed-api-version": "v1",
                "kubevirt.io/storage-observed-api-version": "v1",
            },
            "creationTimestamp": "2024-07-27T17:09:54Z",
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
                    "time": "2024-07-27T17:09:54Z",
                },
                {
                    "apiVersion": "kubevirt.io/v1",
                    "fieldsType": "FieldsV1",
                    "fieldsV1": {"f:spec": {"f:running": {}}},
                    "manager": "kubectl-patch",
                    "operation": "Update",
                    "time": "2024-07-27T17:09:54Z",
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
                    "time": "2024-07-27T17:09:54Z",
                },
                {
                    "apiVersion": "kubevirt.io/v1",
                    "fieldsType": "FieldsV1",
                    "fieldsV1": {
                        "f:status": {
                            ".": {},
                            "f:conditions": {},
                            "f:desiredGeneration": {},
                            "f:observedGeneration": {},
                            "f:printableStatus": {},
                            "f:runStrategy": {},
                            "f:startFailure": {
                                ".": {},
                                "f:consecutiveFailCount": {},
                                "f:lastFailedVMIUID": {},
                                "f:retryAfterTimestamp": {},
                            },
                            "f:volumeSnapshotStatuses": {},
                        }
                    },
                    "manager": "virt-controller",
                    "operation": "Update",
                    "subresource": "status",
                    "time": "2024-07-27T18:27:09Z",
                },
            ],
            "name": "testvm",
            "namespace": "default",
            "resourceVersion": "17403",
            "uid": "4103f114-cf9d-47ad-9af0-be237ce7d4a1",
        },
        "spec": {
            "running": True,
            "template": {
                "metadata": {
                    "creationTimestamp": None,
                    "labels": {"kubevirt.io/domain": "testvm", "kubevirt.io/size": "small"},
                },
                "spec": {
                    "architecture": "arm64",
                    "domain": {
                        "devices": {
                            "disks": [
                                {"disk": {"bus": "virtio"}, "name": "containerdisk"},
                                {"disk": {"bus": "virtio"}, "name": "cloudinitdisk"},
                            ],
                            "interfaces": [{"masquerade": {}, "name": "default"}],
                        },
                        "machine": {"type": "virt"},
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
                    "lastProbeTime": "2024-07-27T18:27:09Z",
                    "lastTransitionTime": "2024-07-27T18:27:09Z",
                    "message": "VMI does not exist",
                    "reason": "VMINotExists",
                    "status": "False",
                    "type": "Ready",
                },
                {"lastProbeTime": None, "lastTransitionTime": None, "status": "True", "type": "LiveMigratable"},
            ],
            "desiredGeneration": 2,
            "observedGeneration": 2,
            "printableStatus": "CrashLoopBackOff",
            "runStrategy": "Always",
            "startFailure": {
                "consecutiveFailCount": 18,
                "lastFailedVMIUID": "f0b6fc58-80b8-4d01-be12-7f029d297970",
                "retryAfterTimestamp": "2024-07-27T18:31:59Z",
            },
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
    }
]

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
