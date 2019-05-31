import os

from mock import MagicMock
from requests import HTTPError

from datadog_checks.dev import get_docker_hostname

VERSION_1_6 = [1, 6, 0]
VERSION_1_8 = [1, 8, 0]

HARBOR_STATUS_CHECKS = [
    # Metric_name, minimum harbor version, requires admin privileges
    ('harbor.status', None, False),
    ('harbor.component.chartmuseum.status', VERSION_1_8, False),
    ('harbor.component.chartmuseum.status', VERSION_1_6, True),
    ('harbor.component.registry.status', VERSION_1_8, False),
    ('harbor.component.redis.status', VERSION_1_8, False),
    ('harbor.component.jobservice.status', VERSION_1_8, False),
    ('harbor.component.registryctl.status', VERSION_1_8, False),
    ('harbor.component.portal.status', VERSION_1_8, False),
    ('harbor.component.core.status', VERSION_1_8, False),
    ('harbor.component.database.status', VERSION_1_8, False),
]

HARBOR_METRICS = [
    # Metric_name, requires admin privileges
    ('harbor.projects.count', False),
    ('harbor.disk.free', True),
    ('harbor.disk.total', True),
]

HERE = os.path.dirname(os.path.abspath(__file__))
HARBOR_VERSION = os.environ['HARBOR_VERSION']
URL = 'http://{}:80'.format(get_docker_hostname())
INSTANCE = {'url': URL, 'username': 'NotAnAdmin', 'password': 'Str0ngPassw0rd'}
ADMIN_INSTANCE = {'url': URL, 'username': 'admin', 'password': 'Harbor12345'}

VOLUME_DISK_FREE = 120000000
VOLUME_DISK_TOTAL = 123456789

USERS_URL = '{base_url}/api/users/'
REGISTRIES_URL = '{base_url}/api/registries'
REGISTRIES_PRE_1_8_URL = '{base_url}/api/targets'


class MockedHarborAPI(object):

    harbor_version = [int(i) for i in HARBOR_VERSION.split('.')]
    with_chartrepo = harbor_version >= VERSION_1_6

    __init__ = MagicMock(return_value=None)

    authenticate = MagicMock()

    health = MagicMock()
    if harbor_version >= VERSION_1_8:
        health.return_value = {
            "status": "healthy",
            "components": [
                {"name": "registryctl", "status": "healthy"},
                {"name": "database", "status": "healthy"},
                {"name": "redis", "status": "healthy"},
                {"name": "chartmuseum", "status": "healthy"},
                {"name": "jobservice", "status": "healthy"},
                {"name": "portal", "status": "healthy"},
                {"name": "core", "status": "healthy"},
                {"name": "registry", "status": "healthy"},
            ],
        }
    else:
        health.side_effect = HTTPError("health endpoint called with version < {}".format(VERSION_1_8))

    ping = MagicMock(return_value="Pong")

    chartrepo_health = MagicMock()
    if with_chartrepo:
        chartrepo_health.return_value = {"healthy": True}
    else:
        chartrepo_health.side_effect = HTTPError(
            "Chartrepo health endpoint called with version < {}".format(VERSION_1_6)
        )

    projects = MagicMock()
    projects.return_value = [
        {
            "project_id": 1,
            "owner_id": 1,
            "name": "library",
            "creation_time": "2019-05-28T20:26:57.968839Z",
            "update_time": "2019-05-28T20:26:57.968839Z",
            "deleted": False,
            "owner_name": "User1",
            "togglable": True,
            "current_user_role_id": 1,
            "repo_count": 0,
            "chart_count": 0,
            "metadata": {"public": "true"},
        },
        {
            "project_id": 2,
            "owner_id": 1,
            "name": "private_repo",
            "creation_time": "2019-05-28T20:26:57.968839Z",
            "update_time": "2019-05-28T20:26:57.968839Z",
            "deleted": False,
            "owner_name": "User2",
            "togglable": True,
            "current_user_role_id": 1,
            "repo_count": 0,
            "chart_count": 0,
            "metadata": {"public": "false"},
        },
    ]

    registries = MagicMock()
    registries.return_value = [
        {
            "id": 1,
            "name": "Demo",
            "type": "harbor",
            "url": "https://demo.goharbor.io/",
            "credential": {"type": "basic", "access_key": "*****", "access_secret": "*****"},
        }
    ]
    if harbor_version >= VERSION_1_8:
        registries.return_value[0]['type'] = 'harbor'
        registries.return_value[0]['status'] = 'healthy'

    registry_health = MagicMock()

    volume_info = MagicMock(return_value={"storage": {"total": VOLUME_DISK_TOTAL, "free": VOLUME_DISK_FREE}})
