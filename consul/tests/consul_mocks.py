# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import random

MOCK_CONFIG = {
    'url': 'http://localhost:8500',
    'catalog_checks': True,
}

MOCK_CONFIG_SERVICE_WHITELIST = {
    'url': 'http://localhost:8500',
    'catalog_checks': True,
    'service_whitelist': ['service_{0}'.format(k) for k in range(70)]
}

MOCK_CONFIG_LEADER_CHECK = {
    'url': 'http://localhost:8500',
    'catalog_checks': True,
    'new_leader_checks': True
}

MOCK_CONFIG_SELF_LEADER_CHECK = {
    'url': 'http://localhost:8500',
    'catalog_checks': True,
    'self_leader_check': True
}

MOCK_CONFIG_NETWORK_LATENCY_CHECKS = {
    'url': 'http://localhost:8500',
    'catalog_checks': True,
    'network_latency_checks': True
}


def mock_check(check, mocks):
    for f_name, m in mocks.iteritems():
        if not hasattr(check, f_name):
            continue
        else:
            setattr(check, f_name, m)


def _get_consul_mocks():
    return {
        'get_services_in_cluster': mock_get_services_in_cluster,
        'get_nodes_with_service': mock_get_nodes_with_service,
        'get_peers_in_cluster': mock_get_peers_in_cluster,
        '_get_local_config': mock_get_local_config,
        '_get_cluster_leader': mock_get_cluster_leader_A,
        '_get_coord_datacenters': mock_get_coord_datacenters,
        '_get_coord_nodes': mock_get_coord_nodes,
        '_get_all_nodes': mock_get_all_nodes,
    }


def _get_random_ip():
    rand_int = int(15 * random.random()) + 10
    return "10.0.2.{0}".format(rand_int)


def mock_get_all_nodes(instance):
    return [{
        'Address': _get_random_ip(),
        'CreateIndex': 25010951,
        'Datacenter': 'dc1',
        'ID': 'node-1',
        'Meta': {},
        'ModifyIndex': 25011022,
        'Node': 'node-1',
        'TaggedAddresses': {'lan': '1.1.1.1', 'wan': '2.2.2.2'}
    }, {
        'Address': _get_random_ip(),
        'CreateIndex': 25010940,
        'Datacenter': 'dc1',
        'ID': 'node-2',
        'Meta': {},
        'ModifyIndex': 25011010,
        'Node': 'node-2',
        'TaggedAddresses': {'lan': '1.1.1.1', 'wan': '2.2.2.2'}
    }]


def mock_get_peers_in_cluster(instance):
    return [
        "10.0.2.14:8300",
        "10.0.2.15:8300",
        "10.0.2.16:8300"
    ]


def mock_get_services_in_cluster(instance):
    return {
        "service-1": [
            "az-us-east-1a"
        ],
        "service-2": [
            "az-us-east-1a"
        ],
        "service-3": [
            "az-us-east-1a"
        ],
        "service-4": [
            "az-us-east-1a"
        ],
        "service-5": [
            "az-us-east-1a"
        ],
        "service-6": [
            "az-us-east-1a"
        ]
    }


def mock_get_n_services_in_cluster(n):
    dct = {}
    for i in range(n):
        k = "service_{0}".format(i)
        dct[k] = []
    return dct


def mock_get_local_config(instance, instance_state):
    return {
        "Config": {
            "AdvertiseAddr": "10.0.2.15",
            "Datacenter": "dc1",
            "Ports": {
                "DNS": 8600,
                "HTTP": 8500,
                "HTTPS": -1,
                "RPC": 8400,
                "SerfLan": 8301,
                "SerfWan": 8302,
                "Server": 8300
            },
        }
    }


def mock_get_nodes_in_cluster(instance):
    return [
        {
            "Address": "10.0.2.15",
            "Node": "node-1"
        },
        {
            "Address": "10.0.2.25",
            "Node": "node-2"
        },
        {
            "Address": "10.0.2.35",
            "Node": "node-2"
        },
    ]


def mock_get_nodes_with_service(instance, service):

    return [
        {
            "Checks": [
                {
                    "CheckID": "serfHealth",
                    "Name": "Serf Health Status",
                    "Node": "node-1",
                    "Notes": "",
                    "Output": "Agent alive and reachable",
                    "ServiceID": "",
                    "ServiceName": "",
                    "Status": "passing"
                },
                {
                    "CheckID": "service:{0}".format(service),
                    "Name": "service check {0}".format(service),
                    "Node": "node-1",
                    "Notes": "",
                    "Output": "Service {0} alive".format(service),
                    "ServiceID": service,
                    "ServiceName": "",
                    "Status": "passing"
                }
            ],
            "Node": {
                "Address": _get_random_ip(),
                "Node": "node-1"
            },
            "Service": {
                "Address": "",
                "ID": service,
                "Port": 80,
                "Service": service,
                "Tags": [
                    "az-us-east-1a"
                ]
            }
        }
    ]


def mock_get_nodes_with_service_warning(instance, service):

    return [
        {
            "Checks": [
                {
                    "CheckID": "serfHealth",
                    "Name": "Serf Health Status",
                    "Node": "node-1",
                    "Notes": "",
                    "Output": "Agent alive and reachable",
                    "ServiceID": "",
                    "ServiceName": "",
                    "Status": "passing"
                },
                {
                    "CheckID": "service:{0}".format(service),
                    "Name": "service check {0}".format(service),
                    "Node": "node-1",
                    "Notes": "",
                    "Output": "Service {0} alive".format(service),
                    "ServiceID": service,
                    "ServiceName": "",
                    "Status": "warning"
                }
            ],
            "Node": {
                "Address": _get_random_ip(),
                "Node": "node-1"
            },
            "Service": {
                "Address": "",
                "ID": service,
                "Port": 80,
                "Service": service,
                "Tags": [
                    "az-us-east-1a"
                ]
            }
        }
    ]


def mock_get_nodes_with_service_critical(instance, service):

    return [
        {
            "Checks": [
                {
                    "CheckID": "serfHealth",
                    "Name": "Serf Health Status",
                    "Node": "node-1",
                    "Notes": "",
                    "Output": "Agent alive and reachable",
                    "ServiceID": "",
                    "ServiceName": "",
                    "Status": "passing"
                },
                {
                    "CheckID": "service:{0}".format(service),
                    "Name": "service check {0}".format(service),
                    "Node": "node-1",
                    "Notes": "",
                    "Output": "Service {0} alive".format(service),
                    "ServiceID": service,
                    "ServiceName": "",
                    "Status": "warning"
                },
                {
                    "CheckID": "service:{0}".format(service),
                    "Name": "service check {0}".format(service),
                    "Node": "node-1",
                    "Notes": "",
                    "Output": "Service {0} alive".format(service),
                    "ServiceID": service,
                    "ServiceName": "",
                    "Status": "critical"
                }
            ],
            "Node": {
                "Address": _get_random_ip(),
                "Node": "node-1"
            },
            "Service": {
                "Address": "",
                "ID": service,
                "Port": 80,
                "Service": service,
                "Tags": [
                    "az-us-east-1a"
                ]
            }
        }
    ]


def mock_get_coord_datacenters(instance):
    return [{
        "Datacenter": "dc1",
        "Coordinates": [
            {
                "Node": "host-1",
                "Coord": {
                    "Vec": [
                        0.036520147625677804,
                        -0.00453289164613373,
                        -0.020523210880196232,
                        -0.02699760529719879,
                        -0.02689207977655939,
                        -0.01993826834797845,
                        -0.013022029942846501,
                        -0.002101656069659926
                    ],
                    "Error": 0.11137306578107628,
                    "Adjustment": -0.00021065907491393056,
                    "Height": 1.1109163532378512e-05
                }
            }]
    }, {
        "Datacenter": "dc2",
        "Coordinates": [
            {
                "Node": "host-2",
                "Coord": {
                    "Vec": [
                        0.03548568620505946,
                        -0.0038202417296129025,
                        -0.01987440114252717,
                        -0.026223108843980016,
                        -0.026581965209197853,
                        -0.01891384862245717,
                        -0.013677323575279184,
                        -0.0014257906933581217
                    ],
                    "Error": 0.06388569381495224,
                    "Adjustment": -0.00036731776343708724,
                    "Height": 8.962823816793629e-05
                }
            }]

    }]


def mock_get_coord_nodes(instance):
    return [{
        "Node": "host-1",
        "Coord": {
            "Vec": [
                0.007682993877165208,
                0.002411059340215172,
                0.0016420746641640123,
                0.0037411046929292906,
                0.004541946058965728,
                0.0032195622863890523,
                -0.0039447666794166095,
                -0.0021767019427297815
            ],
            "Error": 0.28019529748212335,
            "Adjustment": -9.966407036439966e-05,
            "Height": 0.00011777098790169723
        }
    }, {
        "Node": "host-2",
        "Coord": {
            "Vec": [
                0.007725239390196322,
                0.0025160987581685982,
                0.0017412811939227935,
                0.003740935739394932,
                0.004628794642643524,
                0.003190871896051593,
                -0.004058197296573195,
                -0.002108437352702053
            ],
            "Error": 0.31518043241386984,
            "Adjustment": -0.00012274366490350246,
            "Height": 0.00015006836008626717
        }
    }]


def mock_get_health_check(instance, endpoint):
    return [{
        "ModifyIndex": 75214492,
        "CreateIndex": 75214492,
        "Node": "node-1",
        "CheckID": "server-loadbalancer",
        "Name": "Service 'server-loadbalancer' check",
        "Status": "critical",
        "Notes": "",
        "Output": "CheckHttp CRITICAL: Request error: Connection refused - connect(2) for \"localhost\" port 80\n",
        "ServiceID": "server-loadbalancer",
        "ServiceName": "server-loadbalancer",
    },
        {
        "ModifyIndex": 75214492,
        "CreateIndex": 75214492,
        "Node": "node-2",
        "CheckID": "server-loadbalancer",
        "Name": "Service 'server-loadbalancer' check",
        "Status": "passing",
        "Notes": "",
        "Output": "CheckHttp CRITICAL: Request error: Connection refused - connect(2) for \"localhost\" port 80\n",
        "ServiceID": "server-loadbalancer",
        "ServiceName": "server-loadbalancer",
    },
        {
        "ModifyIndex": 75214492,
        "CreateIndex": 75214492,
        "Node": "node-1",
        "CheckID": "server-api",
        "Name": "Service 'server-loadbalancer' check",
        "Status": "passing",
        "Notes": "",
        "Output": "OK",
        "ServiceID": "server-loadbalancer",
        "ServiceName": "server-loadbalancer",
    },
        {
        "ModifyIndex": 75214492,
        "CreateIndex": 75214492,
        "Node": "node-1",
        "CheckID": "server-api",
        "Name": "Service 'server-loadbalancer' check",
        "Status": "passing",
        "Notes": "",
        "Output": "OK",
        "ServiceID": "",
        "ServiceName": "server-loadbalancer",
    },
        {
        "ModifyIndex": 75214492,
        "CreateIndex": 75214492,
        "Node": "node-1",
        "CheckID": "server-api",
        "Name": "Service 'server-loadbalancer' check",
        "Status": "passing",
        "Notes": "",
        "Output": "OK",
        "ServiceID": "server-loadbalancer",
        "ServiceName": "",
    },
        {
        "ModifyIndex": 75214492,
        "CreateIndex": 75214492,
        "Node": "node-1",
        "CheckID": "server-status-empty",
        "Name": "Service 'server-loadbalancer' check",
        "Status": "",
        "Notes": "",
        "Output": "OK",
        "ServiceID": "server-empty",
        "ServiceName": "server-empty",
    }]


def mock_get_cluster_leader_A(instance):
    return '10.0.2.15:8300'


def mock_get_cluster_leader_B(instance):
    return 'My New Leader'
