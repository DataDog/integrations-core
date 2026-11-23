# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from unittest import mock

import pytest

from datadog_checks.kai_scheduler import KaiSchedulerCheck
from datadog_checks.kai_scheduler.kube_client import KubernetesAPIClient

from .common import MOCKED_INSTANCE

pytestmark = [pytest.mark.unit]

# Every field the configuration spec declares, with each supported authentication method.
FULL_KUBECONFIG = {
    'apiVersion': 'v1',
    'kind': 'Config',
    'current-context': 'token',
    'clusters': [
        {
            'name': 'cluster',
            'cluster': {
                'server': 'https://kubernetes.example.com:6443',
                'certificate-authority': '/etc/kubernetes/ca.crt',
                'certificate-authority-data': 'Q0EgZGF0YQ==',
                'insecure-skip-tls-verify': False,
                'tls-server-name': 'kubernetes.example.com',
                'extensions': [
                    {
                        'name': 'client.authentication.k8s.io/exec',
                        'extension': {'audience': 'kubernetes', 'scopes': ['openid', 'email']},
                    }
                ],
            },
        }
    ],
    'contexts': [
        {'name': 'token', 'context': {'cluster': 'cluster', 'user': 'token', 'namespace': 'default'}},
    ],
    'users': [
        {'name': 'token', 'user': {'token': 'my-token', 'tokenFile': '/var/run/secrets/token'}},
        {
            'name': 'client-certificate',
            'user': {
                'client-certificate': '/etc/kubernetes/client.crt',
                'client-certificate-data': 'Q0VSVCBkYXRh',
                'client-key': '/etc/kubernetes/client.key',
                'client-key-data': 'S0VZIGRhdGE=',
            },
        },
        {'name': 'basic', 'user': {'username': 'admin', 'password': 'secret'}},
        {
            'name': 'gcp',
            'user': {
                'auth-provider': {
                    'name': 'gcp',
                    'config': {
                        'access-token': 'access',
                        'expiry': '2026-01-01T00:00:00Z',
                        'cmd-path': '/usr/bin/gcloud',
                        'cmd-args': 'config config-helper --format=json',
                        'scopes': 'https://www.googleapis.com/auth/cloud-platform',
                        'token-key': '{.credential.access_token}',
                        'expiry-key': '{.credential.token_expiry}',
                    },
                }
            },
        },
        {
            'name': 'azure',
            'user': {
                'auth-provider': {
                    'name': 'azure',
                    'config': {
                        'access-token': 'access',
                        'refresh-token': 'refresh',
                        'expires-on': '1767225600',
                        'tenant-id': 'tenant',
                        'client-id': 'client',
                        'apiserver-id': 'apiserver',
                    },
                }
            },
        },
        {
            'name': 'oidc',
            'user': {
                'auth-provider': {
                    'name': 'oidc',
                    'config': {
                        'id-token': 'id',
                        'refresh-token': 'refresh',
                        'client-id': 'client',
                        'client-secret': 'client-secret',
                        'idp-issuer-url': 'https://issuer.example.com',
                        'idp-certificate-authority': '/etc/kubernetes/idp-ca.crt',
                        'idp-certificate-authority-data': 'SURQIENB',
                    },
                }
            },
        },
        {
            'name': 'exec',
            'user': {
                'exec': {
                    'apiVersion': 'client.authentication.k8s.io/v1',
                    'command': 'aws',
                    'args': ['eks', 'get-token', '--cluster-name', 'cluster'],
                    'env': [{'name': 'AWS_PROFILE', 'value': 'default'}],
                    'provideClusterInfo': False,
                }
            },
        },
    ],
}


def kube_config_from_model(kube_config_dict):
    instance = copy.deepcopy(MOCKED_INSTANCE)
    instance['kube_config_dict'] = kube_config_dict
    check = KaiSchedulerCheck('kai_scheduler', {}, [instance])
    check.load_configuration_models()
    return check.config.kube_config_dict


def loaded_kube_config(kube_config_dict):
    """Return the kubeconfig the check passes to the Kubernetes client for the configured `kube_config_dict`."""
    with (
        mock.patch('datadog_checks.kai_scheduler.kube_client.config') as kube_config,
        mock.patch('datadog_checks.kai_scheduler.kube_client.client'),
    ):
        KubernetesAPIClient(kube_config_dict=kube_config_from_model(kube_config_dict))

    if not kube_config.new_client_from_config_dict.called:
        kube_config.load_incluster_config.assert_called_once_with()
        return None
    return kube_config.new_client_from_config_dict.call_args.args[0]


def test_supported_fields_reach_the_kubernetes_client():
    assert loaded_kube_config(FULL_KUBECONFIG) == FULL_KUBECONFIG


def test_unsupported_fields_are_dropped():
    kubeconfig = copy.deepcopy(FULL_KUBECONFIG)
    kubeconfig['preferences'] = {}
    kubeconfig['clusters'][0]['cluster']['proxy-url'] = 'http://proxy.example.com:3128'

    assert loaded_kube_config(kubeconfig) == FULL_KUBECONFIG


@pytest.mark.parametrize('kube_config_dict', [None, {}], ids=['unset', 'empty'])
def test_in_cluster_config_without_kube_config_dict(kube_config_dict):
    assert loaded_kube_config(kube_config_dict) is None


def test_kubernetes_client_uses_the_kube_config_dict():
    kubeconfig = {
        'apiVersion': 'v1',
        'kind': 'Config',
        'current-context': 'default',
        'clusters': [{'name': 'cluster', 'cluster': {'server': 'http://kubernetes.example.com:8080'}}],
        'contexts': [{'name': 'default', 'context': {'cluster': 'cluster', 'user': 'user'}}],
        'users': [{'name': 'user', 'user': {'token': 'my-token'}}],
    }

    kube_client = KubernetesAPIClient(kube_config_dict=kube_config_from_model(kubeconfig))
    configuration = kube_client.api_client.configuration

    assert configuration.host == 'http://kubernetes.example.com:8080'
    assert configuration.api_key['authorization'] == 'Bearer my-token'


def test_kubernetes_client_loads_a_kind_kubeconfig():
    # The shape `kind` and `kubectl` generate, as used by the E2E environment.
    kubeconfig = {
        'apiVersion': 'v1',
        'kind': 'Config',
        'preferences': {},
        'current-context': 'kind-kind',
        'clusters': [
            {
                'name': 'kind-kind',
                'cluster': {'server': 'https://127.0.0.1:6443', 'certificate-authority-data': 'Q0EgZGF0YQ=='},
            }
        ],
        'contexts': [{'name': 'kind-kind', 'context': {'cluster': 'kind-kind', 'user': 'kind-kind'}}],
        'users': [
            {
                'name': 'kind-kind',
                'user': {'client-certificate-data': 'Q0VSVCBkYXRh', 'client-key-data': 'S0VZIGRhdGE='},
            }
        ],
    }

    kube_client = KubernetesAPIClient(kube_config_dict=kube_config_from_model(kubeconfig))
    configuration = kube_client.api_client.configuration

    assert configuration.host == 'https://127.0.0.1:6443'
    for path, content in [
        (configuration.ssl_ca_cert, b'CA data'),
        (configuration.cert_file, b'CERT data'),
        (configuration.key_file, b'KEY data'),
    ]:
        with open(path, 'rb') as f:
            assert f.read() == content
