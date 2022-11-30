import pytest

from datadog_checks.base import ConfigurationError

from .common import HOST, PORT

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    "instance,message",
    [
        (
            {},
            '`web_endpoint` setting must be defined',
        ),
        (
            {'web_endpoint': []},
            '`web_endpoint` setting must be a string',
        ),
        (
            {'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'tags': 'string'},
            '`tags` setting must be a list',
        ),
        (
            {'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'default_tag': []},
            '`default_tag` setting must be a string',
        ),
        (
            {'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'default_include': 'string'},
            '`default_include` setting must be a list',
        ),
        (
            {'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'default_exclude': 'string'},
            '`default_exclude` setting must be a list',
        ),
        (
            {'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'projects': {'keys': [[]]}},
            '`project` key setting must be a string or a dict',
        ),
        (
            {'web_endpoint': 'http://{}:{}'.format(HOST, PORT)},
            '`projects` setting must be defined',
        ),
        (
            {'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'projects': []},
            '`projects` setting must be defined',
        ),
    ],
)
def test_configuration_error(instance, message, sonarqube_check):
    with pytest.raises(ConfigurationError, match=message):
        sonarqube_check(instance)
