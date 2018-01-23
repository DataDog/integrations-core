# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import logging
import mock

# 3p
from docker import Client
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest
from tests.checks.common import load_check
from utils.dockerutil import DockerUtil

log = logging.getLogger('tests')

CONTAINERS_TO_RUN = [
    "nginx:latest",
    "redis:latest",

]

DEFAULT_CUSTOM_TAGS = ["env:test", "docker:test"]

MOCK_CONFIG = {
    "init_config": {},
    "instances": [{
        "url": "unix://var/run/w00t.sock",
        "collect_disk_stats": True,
        "tags": DEFAULT_CUSTOM_TAGS
    }]
}

POD_NAME_LABEL = "io.kubernetes.pod.name"


def reset_docker_settings():
    """Populate docker settings with default, dummy settings"""
    DockerUtil().set_docker_settings({}, {})
    DockerUtil()._client = Client(**DockerUtil().settings)

@attr(requires='docker_daemon')
class TestCheckDockerDaemonDown(AgentCheckTest):
    """Tests for docker_daemon integration when docker is down."""
    CHECK_NAME = 'docker_daemon'

    @mock.patch('docker.client.Client._retrieve_server_version',
                side_effect=Exception("Connection timeout"))
    def test_docker_down(self, *args):
        DockerUtil().set_docker_settings({}, {})
        DockerUtil().last_init_retry = None
        DockerUtil().left_init_retries = 10
        DockerUtil()._client = None
        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertServiceCheck("docker.service_up", status=AgentCheck.CRITICAL, tags=DEFAULT_CUSTOM_TAGS, count=1)

@attr(requires='docker_daemon')
class TestCheckDockerDaemonNoSetUp(AgentCheckTest):
    """Tests for docker_daemon integration that don't need the setUp."""
    CHECK_NAME = 'docker_daemon'

    def test_event_attributes_tag(self):
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "event_attributes_as_tags": ["exitCode", "name"],
            },
            ],
        }

        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])
        DockerUtil().last_init_retry = None
        DockerUtil().left_init_retries = 10
        DockerUtil()._client = None

        container_fail = DockerUtil().client.create_container(
            "nginx:latest", detach=True, name='event-tags-test', entrypoint='/bin/false')
        log.debug('start nginx:latest with entrypoint /bin/false')
        DockerUtil().client.start(container_fail)
        log.debug('container exited with %s' % DockerUtil().client.wait(container_fail, 1))
        # Wait 1 second after exit so the event will be picked up
        from time import sleep
        sleep(1)
        self.run_check(config, force_reload=True)
        DockerUtil().client.remove_container(container_fail)

        # Previous tests might have left unprocessed events, to be ignored
        filtered_events = []
        for event in self.events:
            if 'container_name:event-tags-test' in event.get('tags', []):
                filtered_events.append(event)

        self.assertEqual(len(filtered_events), 1)
        self.assertIn("exitCode:1", filtered_events[0]["tags"])
        self.assertNotIn("name:test-exit-fail", filtered_events[0]["tags"])

@attr(requires='docker_daemon')
class TestCheckDockerDaemon(AgentCheckTest):
    """Basic Test for docker_daemon integration."""
    CHECK_NAME = 'docker_daemon'

    # Mock tests #

    def mock_normal_get_info(self):
        return {
            'DriverStatus': [
                ['Data Space Used', '1 GB'],
                ['Data Space Available', '9 GB'],
                ['Data Space Total', '10 GB'],
                ['Metadata Space Used', '1 MB'],
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
            ]
        }

    def mock_get_info_no_used(self):
        return {
            'DriverStatus': [
                ['Data Space Available', '9 GB'],
                ['Data Space Total', '10 GB'],
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
            ]
        }

    def mock_get_info_no_data(self):
        return {
            'DriverStatus': [
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
                ['Metadata Space Used', '1 MB'],
            ]
        }

    def mock_get_info_invalid_values(self):
        return {
            'DriverStatus': [
                ['Metadata Space Available', '9 MB'],
                ['Metadata Space Total', '10 MB'],
                ['Metadata Space Used', '11 MB'],
            ]
        }

    def mock_get_info_all_zeros(self):
        return {
            'DriverStatus': [
                ['Data Space Available', '0 MB'],
                ['Data Space Total', '0 GB'],
                ['Data Space Used', '0 KB'],
            ]
        }

    def mock_get_info_no_spaces(self):
        return {
            'DriverStatus': [
                ['Data Space Used', '1GB'],
                ['Data Space Available', '9GB'],
                ['Data Space Total', '10GB'],
                ['Metadata Space Used', '1MB'],
                ['Metadata Space Available', '9MB'],
                ['Metadata Space Total', '10MB'],
            ]
        }

    @mock.patch('docker.Client.info')
    def test_main_service_check(self, mock_info):
        mock_info.return_value = self.mock_normal_get_info()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertServiceCheck("docker.service_up", status=AgentCheck.OK, tags=DEFAULT_CUSTOM_TAGS, count=1)

    @mock.patch('docker.Client.info')
    def test_devicemapper_disk_metrics(self, mock_info):
        mock_info.return_value = self.mock_normal_get_info()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.data.free', value=9e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.used', value=1e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.total', value=10e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.percent', value=10.0, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.free', value=9e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.used', value=1e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.total', value=10e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.percent', value=10.0, tags=DEFAULT_CUSTOM_TAGS)

    @mock.patch('docker.Client.info')
    def test_devicemapper_no_used_info(self, mock_info):
        """Disk metrics collection should still work and `percent` can be calculated"""
        mock_info.return_value = self.mock_get_info_no_used()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.data.free', value=9e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.total', value=10e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.percent', value=10.0, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.free', value=9e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.total', value=10e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.percent', value=10.0, tags=DEFAULT_CUSTOM_TAGS)

    @mock.patch('docker.Client.info')
    def test_devicemapper_no_data_info(self, mock_info):
        """Disk metrics collection should still partially work for metadata"""
        mock_info.return_value = self.mock_get_info_no_data()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.metadata.free', value=9e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.total', value=10e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.percent', value=10.0, tags=DEFAULT_CUSTOM_TAGS)

    @mock.patch('docker.Client.info')
    def test_devicemapper_invalid_values(self, mock_info):
        """Invalid values are detected in _calc_percent_disk_stats and 'percent' use 'free'+'used' instead of 'total' """
        mock_info.return_value = self.mock_get_info_invalid_values()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.metadata.free', value=9e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.used', value=11e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.total', value=10e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.percent', value=55, tags=DEFAULT_CUSTOM_TAGS)

    @mock.patch('docker.Client.info')
    def test_devicemapper_all_zeros(self, mock_info):
        """Percentage should not be calculated, other metrics should be collected correctly"""
        mock_info.return_value = self.mock_get_info_all_zeros()

        self.run_check(MOCK_CONFIG, force_reload=True)
        metric_names = [metric[0] for metric in self.metrics]
        self.assertMetric('docker.data.free', value=0, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.used', value=0, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.total', value=0, tags=DEFAULT_CUSTOM_TAGS)
        self.assertNotIn('docker.data.percent', metric_names)

    @mock.patch('docker.Client.info')
    def test_devicemapper_no_spaces(self, mock_info):
        mock_info.return_value = self.mock_get_info_no_spaces()

        self.run_check(MOCK_CONFIG, force_reload=True)
        self.assertMetric('docker.data.free', value=9e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.used', value=1e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.total', value=10e9, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.data.percent', value=10.0, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.free', value=9e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.used', value=1e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.total', value=10e6, tags=DEFAULT_CUSTOM_TAGS)
        self.assertMetric('docker.metadata.percent', value=10.0, tags=DEFAULT_CUSTOM_TAGS)

    # integration tests #

    def setUp(self):
        self.docker_client = DockerUtil().client

        self.second_network = self.docker_client.create_network("second", driver="bridge")['Id']

        for c in CONTAINERS_TO_RUN:
            images = [i["RepoTags"][0] for i in self.docker_client.images(c.split(":")[0]) if i["RepoTags"] and i["RepoTags"][0].startswith(c)]
            if len(images) == 0:
                for line in self.docker_client.pull(c, stream=True):
                    print line

        self.containers = []
        for c in CONTAINERS_TO_RUN:
            name = "test-new-{0}".format(c.replace(":", "-"))
            host_config = None
            labels = None
            if c == "nginx:latest":
                host_config = {"Memory": 137438953472}
                labels = {"label1": "nginx", "foo": "bar"}

            cont = self.docker_client.create_container(
                c, detach=True, name=name, host_config=host_config, labels=labels)
            self.containers.append(cont)

            if c == "nginx:latest":
                self.docker_client.connect_container_to_network(cont['Id'], self.second_network)

        for c in self.containers:
            log.info("Starting container: {0}".format(c))
            self.docker_client.start(c)

    def tearDown(self):
        for c in self.containers:
            log.info("Stopping container: {0}".format(c))
            self.docker_client.remove_container(c, force=True)
        self.docker_client.remove_network(self.second_network)

    def test_basic_config_single(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.image.size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.mem.cache', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest'])
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_image_size": True,
                "collect_images_stats": True
            },
            ],
        }
        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_basic_config_twice(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.cpu.system', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.cpu.system', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.user', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.cpu.user', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.read_bytes', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.io.read_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.write_bytes', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.io.write_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),

            ('docker.net.bytes_rcvd', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'docker_network:bridge']),
            ('docker.net.bytes_rcvd', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'docker_network:bridge']),
            ('docker.net.bytes_sent', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'docker_network:bridge']),
            ('docker.net.bytes_sent', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'docker_network:bridge'])
        ]

        custom_tags = ["extra_tag", "env:testing"]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "tags": custom_tags,
                "collect_image_size": True,
                "collect_images_stats": True,
            },
            ],
        }
        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])

        self.run_check_twice(config, force_reload=True)
        for mname, tags in expected_metrics:
            expected_tags = list(custom_tags)
            if tags is not None:
                expected_tags += tags
            self.assertMetric(mname, tags=expected_tags, count=1, at_least=1)

    def test_exclude_filter(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.cpu.system', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.user', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.io.read_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.write_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_rcvd', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'docker_network:bridge']),
            ('docker.net.bytes_sent', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'docker_network:bridge'])
        ]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "exclude": ["docker_image:nginx"],
                "collect_images_stats": True,
                "collect_image_size": True,
            },
            ],
        }
        DockerUtil._drop()
        DockerUtil(init_config=config['init_config'], instance=config['instances'][0])

        self.run_check_twice(config, force_reload=True)

        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

        perf_metrics = [
            "docker.cpu.system",
            "docker.cpu.user",
            "docker.io.read_bytes",
            "docker.io.write_bytes",
            "docker.mem.cache",
            "docker.mem.rss",
            "docker.net.bytes_rcvd",
            "docker.net.bytes_sent"
        ]

        nginx_tags = ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest',
                      'image_name:nginx', 'image_tag:latest']
        for mname in perf_metrics:
            self.assertMetric(mname, tags=nginx_tags, count=0)

    def test_include_filter(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.cpu.system', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.cpu.user', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.io.read_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.io.write_bytes', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.net.bytes_rcvd', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'docker_network:bridge']),
            ('docker.net.bytes_sent', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'docker_network:bridge'])
        ]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "include": ["image_name:redis"],
                "exclude": [".*"],
                "collect_images_stats": True,
                "collect_image_size": True,
            },
            ],
        }
        DockerUtil._drop()
        DockerUtil(init_config=config['init_config'], instance=config['instances'][0])

        self.run_check_twice(config, force_reload=True)

        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

        perf_metrics = [
            "docker.cpu.system",
            "docker.cpu.user",
            "docker.io.read_bytes",
            "docker.io.write_bytes",
            "docker.mem.cache",
            "docker.mem.rss",
            "docker.net.bytes_rcvd",
            "docker.net.bytes_sent"
        ]

        nginx_tags = ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']
        for m in perf_metrics:
            self.assertMetric(mname, tags=nginx_tags, count=0)

    def test_tags_options(self):
        expected_metrics = [
            ('docker.containers.running', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.containers.running', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.containers.stopped', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.containers.stopped', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.cpu.system', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.cpu.system', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.cpu.user', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.cpu.user', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.io.read_bytes', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.io.read_bytes', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.io.write_bytes', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.io.write_bytes', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.mem.cache', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.mem.cache', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.mem.rss', ['container_command:docker-entrypoint.sh redis-server']),
            ('docker.mem.rss', ["container_command:nginx -g 'daemon off;'"]),
            ('docker.net.bytes_rcvd', ['container_command:docker-entrypoint.sh redis-server', 'docker_network:bridge']),
            ('docker.net.bytes_rcvd', ["container_command:nginx -g 'daemon off;'", 'docker_network:bridge']),
            ('docker.net.bytes_sent', ["container_command:nginx -g 'daemon off;'", 'docker_network:bridge']),
            ('docker.net.bytes_sent', ['container_command:docker-entrypoint.sh redis-server', 'docker_network:bridge'])
        ]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "performance_tags": ["container_command"],
                "container_tags": ["container_command"],
                "collect_images_stats": True,
                "collect_image_size": True,
            },
            ],
        }
        DockerUtil._drop()
        DockerUtil(init_config=config['init_config'], instance=config['instances'][0])

        self.run_check_twice(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_set_docker_settings(self):
        """Test a client settings update"""
        self.assertEqual(DockerUtil().settings["version"], "auto")
        cur_loc = __file__
        init_config = {
            "api_version": "foobar",
            "timeout": "42",
            "tls_client_cert": cur_loc,
            "tls_client_key": cur_loc,
            "tls_cacert": cur_loc,
            "tls": True
        }

        instance = {
            "url": "https://foo.bar:42",
        }

        DockerUtil().set_docker_settings(init_config, instance)
        DockerUtil()._client = Client(**DockerUtil().settings)
        self.assertEqual(DockerUtil().client.verify, cur_loc)
        self.assertEqual(DockerUtil().client.cert, (cur_loc, cur_loc))
        reset_docker_settings()

    def test_labels_collection(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx', 'short_image:nginx:latest']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx', 'short_image:nginx:latest']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.mem.cache', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
            ('docker.mem.in_use', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_labels_as_tags": ["label1"],
                "collect_image_size": True,
                "collect_images_stats": True,
                "collect_container_count": True,
                "collect_dead_container_count": True,
                "collect_exited_container_count": True,
                "collect_volume_count": True,
                "collect_dangling_volume_count": True,
            },
            ],
        }
        DockerUtil._drop()
        DockerUtil(init_config=config['init_config'], instance=config['instances'][0])

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_collect_labels_as_tags(self):
        expected_metrics = [
            ('docker.containers.stopped.total', None),
            ('docker.containers.running.total', None),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest', 'label1:nginx']),
            ('docker.mem.rss', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest', 'label1:nginx']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
            ('docker.mem.cache', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.in_use', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'label1:nginx']),
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
            },
            ],
        }

        DockerUtil._drop()
        DockerUtil(init_config=config['init_config'], instance=config['instances'][0])

        self.agentConfig = {
            'docker_labels_as_tags': 'label1'
        }
        self.check = load_check('docker_daemon', config, self.agentConfig)

        self.run_check(config)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_histogram(self):

        metric_suffix = ["count", "avg", "median", "max", "95percentile"]

        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
        ]

        histo_metrics = [
            ('docker.mem.cache', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.cache', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.rss', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.in_use', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_image_size": True,
                "collect_images_stats": True,
                "use_histogram": True,
            },
            ],
        }
        DockerUtil._drop()
        DockerUtil(init_config=config['init_config'], instance=config['instances'][0])

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

        for mname, tags in histo_metrics:
            for suffix in metric_suffix:
                self.assertMetric(mname + "." + suffix, tags=tags, at_least=1)

    def test_events(self):
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_images_stats": True,
            },
            ],
        }

        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])

        self.run_check(config, force_reload=True)
        self.assertEqual(len(self.events), 2)

    def test_healthcheck(self):
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "health_service_check_whitelist": ["docker_image:nginx", "docker_image:redis"],
            },
            ],
        }

        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])
        DockerUtil().filtering_enabled = False

        self.run_check(config, force_reload=True)
        self.assertServiceCheck('docker.container_health', count=2)

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "health_service_check_whitelist": [],
            },
            ],
        }

        DockerUtil._drop()
        DockerUtil(init_config=config['init_config'], instance=config['instances'][0])

        self.run_check(config, force_reload=True)
        self.assertServiceCheck('docker.container_health', count=0)


    def test_container_size(self):
        expected_metrics = [
            ('docker.containers.running', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:redis:latest', 'image_name:redis', 'image_tag:latest', 'short_image:redis:latest']),
            ('docker.containers.stopped', ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'short_image:nginx:latest']),
            ('docker.containers.running.total', None),
            ('docker.containers.stopped.total', None),
            ('docker.image.size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:redis', 'image_tag:latest']),
            ('docker.image.virtual_size', ['image_name:nginx', 'image_tag:latest']),
            ('docker.images.available', None),
            ('docker.images.intermediate', None),
            ('docker.mem.cache', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.cache', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.rss', ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ('docker.mem.limit', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ('docker.mem.in_use', ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            # Container size metrics
            ("docker.container.size_rootfs", ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
            ("docker.container.size_rootfs", ['container_name:test-new-redis-latest', 'docker_image:redis:latest', 'image_name:redis', 'image_tag:latest']),
            ("docker.container.size_rw", ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest']),
        ]

        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_container_size": True,
                "collect_image_size": True,
                "collect_images_stats": True,
            },
            ],
        }
        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])

        self.run_check(config, force_reload=True)
        for mname, tags in expected_metrics:
            self.assertMetric(mname, tags=tags, count=1, at_least=1)

    def test_image_tags_extraction(self):
        entities = [
            # ({'Image': image_name}, [expected_image_name, expected_image_tag])
            ({'Image': 'nginx:latest'}, [['nginx'], ['latest']]),
            ({'Image': 'localhost/nginx:latest'}, [['localhost/nginx'], ['latest']]),
            ({'Image': 'localhost:5000/nginx:latest'}, [['localhost:5000/nginx'], ['latest']]),
            ({'RepoTags': ['redis:latest']}, [['redis'], ['latest']]),
            ({'RepoTags': ['localhost/redis:latest']}, [['localhost/redis'], ['latest']]),
            ({'RepoTags': ['localhost:5000/redis:latest']}, [['localhost:5000/redis'], ['latest']]),
            ({'RepoTags': ['localhost:5000/redis:latest', 'localhost:5000/redis:v1.1']}, [['localhost:5000/redis'], ['latest', 'v1.1']]),
            ({'RepoTags': [], 'RepoDigests': [u'datadog/docker-dd-agent@sha256:47a59c2ea4f6d9555884aacc608b303f18bde113b1a3a6743844bfc364d73b44']},
                [['datadog/docker-dd-agent'], None]),
        ]
        for entity in entities:
            self.assertEqual(sorted(DockerUtil().image_tag_extractor(entity[0], 0)), sorted(entity[1][0]))
            tags = DockerUtil().image_tag_extractor(entity[0], 1)
            if isinstance(entity[1][1], list):
                self.assertEqual(sorted(tags), sorted(entity[1][1]))
            else:
                self.assertEqual(tags, entity[1][1])

    def test_container_name_extraction(self):
        containers = [
            ({'Id': 'deadbeef'}, ['deadbeef']),
            ({'Names': ['/redis'], 'Id': 'deadbeef'}, ['redis']),
            ({'Names': ['/mongo', '/redis/mongo'], 'Id': 'deadbeef'}, ['mongo']),
            ({'Names': ['/redis/mongo', '/mongo'], 'Id': 'deadbeef'}, ['mongo']),
        ]
        for co in containers:
            self.assertEqual(DockerUtil.container_name_extractor(co[0]), co[1])

    def test_collect_exit_code(self):
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "collect_exit_codes": True
            }]
        }
        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])

        expected_service_checks = [
            (AgentCheck.OK, ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'container_name:test-exit-ok', 'short_image:nginx:latest']),
            (AgentCheck.CRITICAL, ['docker_image:nginx:latest', 'image_name:nginx', 'image_tag:latest', 'container_name:test-exit-fail', 'short_image:nginx:latest']),
        ]

        container_ok = self.docker_client.create_container(
            "nginx:latest", detach=True, name='test-exit-ok', entrypoint='/bin/true')
        log.debug('start nginx:latest with entrypoint /bin/true')
        container_fail = self.docker_client.create_container(
            "nginx:latest", detach=True, name='test-exit-fail', entrypoint='/bin/false')
        log.debug('start nginx:latest with entrypoint /bin/false')
        self.docker_client.start(container_ok)
        self.docker_client.start(container_fail)
        log.debug('container exited with %s' % self.docker_client.wait(container_ok, 1))
        log.debug('container exited with %s' % self.docker_client.wait(container_fail, 1))
        # After the container exits, we need to wait a second so the event isn't too recent
        # when the check runs, otherwise the event is not picked up
        from time import sleep
        sleep(1)

        self.run_check(config)
        self.docker_client.remove_container(container_ok)
        self.docker_client.remove_container(container_fail)

        for status, tags in expected_service_checks:
            self.assertServiceCheck('docker.exit', status=status, tags=tags, count=1)

    def test_network_tagging(self):
        expected_metrics = [
            ('docker.net.bytes_rcvd',
             ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx',
              'image_tag:latest', 'docker_network:bridge']),
            ('docker.net.bytes_rcvd',
             ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx',
              'image_tag:latest', 'docker_network:second']),
            ('docker.net.bytes_sent',
             ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx',
              'image_tag:latest', 'docker_network:bridge']),
            ('docker.net.bytes_sent',
             ['container_name:test-new-nginx-latest', 'docker_image:nginx:latest', 'image_name:nginx',
              'image_tag:latest', 'docker_network:second'])
        ]

        custom_tags = ["extra_tag", "env:testing"]
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "tags": custom_tags,
                "collect_image_size": True,
                "collect_images_stats": True,
            },
            ],
        }
        DockerUtil().set_docker_settings(config['init_config'], config['instances'][0])

        self.run_check_twice(config, force_reload=True)
        for mname, tags in expected_metrics:
            expected_tags = list(custom_tags)
            if tags is not None:
                expected_tags += tags
            self.assertMetric(mname, tags=expected_tags, count=1, at_least=1)

    def mock_parse_cgroup_file(self, stat_file):
        with open(stat_file, 'r') as fp:
            if 'blkio' in stat_file:
                return {}
            elif 'cpuacct.usage' in stat_file:
                return dict({'usage': str(int(fp.read())/10000000)})
            # mocked part
            elif 'cpu' in stat_file:
                return {'user': 1000 * self.run, 'system': 1000 * self.run}
                self.run += 1
            elif 'memory.soft_limit_in_bytes' in stat_file:
                    value = int(fp.read())
                    if value < 2 ** 60:
                        return dict({'softlimit': value})
            else:
                return dict(map(lambda x: x.split(' ', 1), fp.read().splitlines()))

    def test_filter_capped_metrics(self):
        config = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/docker.sock",
                "capped_metrics": {
                    "docker.cpu.user": 100,
                    "docker.cpu.system": 100,
                }
            }]
        }
        self.run = 1
        self.run_check_twice(config, mocks={'_parse_cgroup_file': self.mock_parse_cgroup_file})
        # last 2 points should be dropped so the rate should be 0
        self.assertMetric('docker.cpu.user', value=0.0)
        self.assertMetric('docker.cpu.system', value=0.0)

    def test_filter_event_type(self):
        """ Testing event type filtering"""
        event_list = [
            {"status":"create","id":"aa717771661fb29ed0ca74274178dbc7114dee3d4adfde7760828ee3f6b52001","from":"redis","Type":"container","Action":"create","Actor":{"ID":"aa717771661fb29ed0ca74274178dbc7114dee3d4adfde7760828ee3f6b52001","Attributes":{"image":"redis","name":"brave_rosalind"}},"scope":"local","time":1505221851,"timeNano":1505221851874332240},
            {"status":"pause","id":"aa717771661fb29ed0ca74274178dbc7114dee3d4adfde7760828ee3f6b52001","from":"redis","Type":"container","Action":"pause","Actor":{"ID":"aa717771661fb29ed0ca74274178dbc7114dee3d4adfde7760828ee3f6b52001","Attributes":{"image":"redis","name":"brave_rosalind"}},"scope":"local","time":1505221892,"timeNano":1505221892885900077},
            {"status":"top","id":"aa717771661fb29ed0ca74274178dbc7114dee3d4adfde7760828ee3f6b52001","from":"redis","Type":"container","Action":"top","Actor":{"ID":"aa717771661fb29ed0ca74274178dbc7114dee3d4adfde7760828ee3f6b52001","Attributes":{"image":"redis","name":"brave_rosalind"}},"scope":"local","time":1505221910,"timeNano":1505221910331861955},
        ]
        dict_mock = {"redis":event_list}

        # Testing with the default config
        self.run_check(MOCK_CONFIG, force_reload=True)
        result = self.check._format_events(dict_mock, {})

        self.assertEqual(1, len(result))
        self.assertIn('create', result[0]['msg_text'])
        self.assertIn('pause', result[0]['msg_text'])
        self.assertNotIn('top', result[0]['msg_text'])

        # Testing with a custom config
        mock_config_top = {
            "init_config": {},
            "instances": [{
                "url": "unix://var/run/w00t.sock",
                "filtered_event_types": ["pause"]
            }]
        }
        self.run_check(mock_config_top, force_reload=True)
        resulttop = self.check._format_events(dict_mock, {})

        self.assertEqual(1, len(resulttop))
        self.assertIn('create', resulttop[0]['msg_text'])
        self.assertNotIn('pause', resulttop[0]['msg_text'])
        self.assertIn('top', resulttop[0]['msg_text'])
