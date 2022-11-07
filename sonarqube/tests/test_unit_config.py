import pytest

from datadog_checks.base import ConfigurationError

from .common import HOST, PORT

pytestmark = [pytest.mark.unit]


def test_web_endpoint_not_defined_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'web_endpoint\' setting must be defined'):
        sonarqube_check({})


def test_web_endpoint_not_string_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'web_endpoint\' setting must be a string'):
        sonarqube_check({'web_endpoint': []})


def test_tags_not_list_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'tags\' setting must be a list'):
        sonarqube_check({'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'tags': 'string'})


def test_default_tag_not_string_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'default_tag\' setting must be a string'):
        sonarqube_check({'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'default_tag': []})


def test_default_include_not_list_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'default_include\' setting must be a list'):
        sonarqube_check({'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'default_include': 'string'})


def test_default_exclude_not_list_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'default_exclude\' setting must be a list'):
        sonarqube_check({'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'default_exclude': 'string'})


def test_project_key_not_dict_or_string_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='project key setting must be a string or a dict'):
        sonarqube_check({'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'projects': {'keys': [[]]}})


def test_not_projects_not_components_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'projects\' setting must be defined'):
        sonarqube_check({'web_endpoint': 'http://{}:{}'.format(HOST, PORT)})


def test_projects_key_not_dict_raises_configuration_error(sonarqube_check):
    with pytest.raises(ConfigurationError, match='\'projects\' setting must be defined'):
        sonarqube_check({'web_endpoint': 'http://{}:{}'.format(HOST, PORT), 'projects': []})
