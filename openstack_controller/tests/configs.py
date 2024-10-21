# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH = os.path.join(CONFIG_DIR, 'openstack_config_unit_tests.yaml')
TEST_OPENSTACK_CONFIG_E2E_PATH = os.path.join(CONFIG_DIR, 'openstack_config.yaml')
TEST_OPENSTACK_UPDATED_CONFIG_E2E_PATH = os.path.join(CONFIG_DIR, 'openstack_config_updated.yaml')
TEST_OPENSTACK_BAD_CONFIG_PATH = os.path.join(CONFIG_DIR, 'openstack_bad_config.yaml')

REST = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'use_legacy_check_version': False,
}

REST_EXCLUDING_DEMO_PROJECT = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'use_legacy_check_version': False,
    'projects': {
        'include': ['.*'],
        'exclude': ['^demo.*'],
    },
}

REST_EXCLUDING_DEV_SERVERS = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'use_legacy_check_version': False,
    'projects': {
        'include': [
            {
                "name": "^admin.*",
                "compute": {
                    "servers": {
                        "include": [
                            "^admin.*",
                        ],
                        "exclude": [
                            "^dev.*",
                        ],
                    },
                },
            },
            "^demo.*",
        ],
    },
}

REST_DEMO_SERVERS_COLLECT_FALSE = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": False,
                },
            },
        ],
    },
}

REST_DEMO_SERVERS_DIAGNOSTICS_FALSE = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "diagnostics": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

REST_DEMO_SERVERS_FLAVORS_FALSE = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "flavors": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

REST_NOVA_MICROVERSION_2_93 = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
}

REST_NOVA_MICROVERSION_2_93_EXCLUDING_DEMO_PROJECT = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    'projects': {
        'include': ['.*'],
        'exclude': ['^demo.*'],
    },
}

REST_NOVA_MICROVERSION_2_93_EXCLUDING_DEV_SERVERS = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    'projects': {
        'include': [
            {
                "name": "^admin.*",
                "compute": {
                    "servers": {
                        "include": [
                            "^admin.*",
                        ],
                        "exclude": [
                            "^dev.*",
                        ],
                    },
                },
            },
            "^demo.*",
        ],
    },
}

REST_NOVA_MICROVERSION_2_93_DEMO_SERVERS_DIAGNOSTICS_FALSE = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "diagnostics": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

REST_NOVA_MICROVERSION_2_93_DEMO_SERVERS_FLAVORS_FALSE = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "flavors": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

REST_IRONIC_MICROVERSION_1_80 = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'ironic_microversion': '1.80',
    'use_legacy_check_version': False,
}

REST_MICROVERSION_3_70 = {
    'keystone_server_url': 'http://127.0.0.1:8080/identity',
    'username': 'admin',
    'password': 'password',
    'cinder_microversion': 'volume 3.70',
    'use_legacy_check_version': False,
}

SDK = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'use_legacy_check_version': False,
}

SDK_EXCLUDING_DEMO_PROJECT = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'use_legacy_check_version': False,
    'projects': {
        'include': ['.*'],
        'exclude': ['^demo.*'],
    },
}

SDK_EXCLUDING_DEV_SERVERS = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'use_legacy_check_version': False,
    'projects': {
        'include': [
            {
                "name": "^admin.*",
                "compute": {
                    "servers": {
                        "include": [
                            "^admin.*",
                        ],
                        "exclude": [
                            "^dev.*",
                        ],
                    },
                },
            },
            "^demo.*",
        ],
    },
}

SDK_DEMO_SERVERS_COLLECT_FALSE = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": False,
                },
            },
        ],
    },
}

SDK_DEMO_SERVERS_DIAGNOSTICS_FALSE = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "diagnostics": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

SDK_DEMO_SERVERS_FLAVORS_FALSE = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "flavors": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

SDK_NOVA_MICROVERSION_2_93 = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
}

SDK_NOVA_MICROVERSION_2_93_DEMO_SERVERS_DIAGNOSTICS_FALSE = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "diagnostics": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

SDK_NOVA_MICROVERSION_2_93_EXCLUDING_DEMO_PROJECT = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    'projects': {
        'include': ['.*'],
        'exclude': ['^demo.*'],
    },
}

SDK_NOVA_MICROVERSION_2_93_EXCLUDING_DEV_SERVERS = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    'projects': {
        'include': [
            {
                "name": "^admin.*",
                "compute": {
                    "servers": {
                        "include": [
                            "^admin.*",
                        ],
                        "exclude": [
                            "^dev.*",
                        ],
                    },
                },
            },
            "^demo.*",
        ],
    },
}

SDK_NOVA_MICROVERSION_2_93_DEMO_SERVERS_FLAVORS_FALSE = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'nova_microversion': '2.93',
    'use_legacy_check_version': False,
    "projects": {
        "include": [
            {
                "name": "^admin.*",
            },
            {
                "name": "^demo.*",
                "compute": {
                    "servers": {
                        "include": [
                            {
                                "name": ".*",
                                "flavors": False,
                            },
                        ],
                    },
                },
            },
        ],
    },
}

SDK_IRONIC_MICROVERSION_1_80 = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'ironic_microversion': '1.80',
    'use_legacy_check_version': False,
}

SDK_MICROVERSION_3_70 = {
    'openstack_cloud_name': 'test_cloud',
    'openstack_config_file_path': TEST_OPENSTACK_CONFIG_UNIT_TESTS_PATH,
    'cinder_microversion': 'volume 3.70',
    'use_legacy_check_version': False,
}
