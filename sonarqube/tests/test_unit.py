# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError

pytestmark = [pytest.mark.unit]


class TestParseConfig:
    def test_components_not_mapping(self, sonarqube_check):
        check = sonarqube_check({'components': 'foo'})

        with pytest.raises(ConfigurationError, match='The `components` setting must be a mapping'):
            check.parse_config()

    def test_components_not_defined(self, sonarqube_check):
        check = sonarqube_check({})

        with pytest.raises(ConfigurationError, match='The `components` setting must be defined'):
            check.parse_config()

    def test_components_empty(self, sonarqube_check):
        check = sonarqube_check({'components': {}})

        with pytest.raises(ConfigurationError, match='The `components` setting must be defined'):
            check.parse_config()

    def test_default_tag_not_string(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_tag': 9000})

        with pytest.raises(ConfigurationError, match='The `default_tag` setting must be a string'):
            check.parse_config()

    def test_component_not_mapping(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': 'bar'}})

        with pytest.raises(ConfigurationError, match='Component `foo` must refer to a mapping'):
            check.parse_config()

    def test_tag_not_string(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'tag': 9000}}})

        with pytest.raises(ConfigurationError, match='The `tag` setting must be a string'):
            check.parse_config()


class TestPatternCompilation:
    def test_default_include_not_array(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_include': 'foo'})

        with pytest.raises(ConfigurationError, match='The `default_include` setting must be an array'):
            check.parse_config()

    def test_default_include_pattern_not_string(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_include': [9000]})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `default_include` setting must be a string'):
            check.parse_config()

    def test_default_include_pattern_too_broad(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_include': ['sonarqube']})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `default_include` setting must be more specific'):
            check.parse_config()

    def test_default_exclude_not_array(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_exclude': 'foo'})

        with pytest.raises(ConfigurationError, match='The `default_exclude` setting must be an array'):
            check.parse_config()

    def test_default_exclude_pattern_not_string(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_exclude': [9000]})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `default_exclude` setting must be a string'):
            check.parse_config()

    def test_default_exclude_pattern_too_broad(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_exclude': ['sonarqube']})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `default_exclude` setting must be more specific'):
            check.parse_config()

    def test_include_not_array(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'include': 'foo'}}})

        with pytest.raises(ConfigurationError, match='The `include` setting must be an array'):
            check.parse_config()

    def test_include_pattern_not_string(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'include': [9000]}}})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `include` setting must be a string'):
            check.parse_config()

    def test_include_pattern_too_broad(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'include': ['sonarqube']}}})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `include` setting must be more specific'):
            check.parse_config()

    def test_exclude_not_array(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'exclude': 'foo'}}})

        with pytest.raises(ConfigurationError, match='The `exclude` setting must be an array'):
            check.parse_config()

    def test_exclude_pattern_not_string(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'exclude': [9000]}}})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `exclude` setting must be a string'):
            check.parse_config()

    def test_exclude_pattern_too_broad(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'exclude': ['sonarqube']}}})

        with pytest.raises(ConfigurationError, match='Pattern #1 in `exclude` setting must be more specific'):
            check.parse_config()


class TestComponentData:
    def test_data_is_present(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}, 'bar': {}}})

        check.parse_config()

        assert len(check._components) == 2
        assert 'foo' in check._components
        assert 'bar' in check._components

    def test_default_default_tag(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}})

        check.parse_config()
        tag_name, _ = check._components['foo']

        assert tag_name == 'component'

    def test_default_tag(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_tag': 'project'})

        check.parse_config()
        tag_name, _ = check._components['foo']

        assert tag_name == 'project'

    def test_tag_override(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'tag': 'bar'}}, 'default_tag': 'project'})

        check.parse_config()
        tag_name, _ = check._components['foo']

        assert tag_name == 'bar'

    def test_selector_accept_everything_by_default(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}})

        check.parse_config()
        _, selector = check._components['foo']

        assert selector('asdf')

    def test_selector_default_include(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {}}, 'default_include': ['foo.']})

        check.parse_config()
        _, selector = check._components['foo']

        assert selector('foo.bar')
        assert not selector('bar.baz')

    def test_selector_include_override(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'include': ['bar.']}}, 'default_include': ['foo.']})

        check.parse_config()
        _, selector = check._components['foo']

        assert not selector('foo.bar')
        assert selector('bar.baz')

    def test_selector_default_exclude_override(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'include': ['foo.']}}, 'default_exclude': ['foo.bar']})

        check.parse_config()
        _, selector = check._components['foo']

        assert not selector('foo.bar')
        assert selector('foo.baz')

    def test_selector_exclude_override(self, sonarqube_check):
        check = sonarqube_check(
            {'components': {'foo': {'include': ['foo.'], 'exclude': ['foo.baz']}}, 'default_exclude': ['foo.bar']}
        )

        check.parse_config()
        _, selector = check._components['foo']

        assert selector('foo.bar')
        assert not selector('foo.baz')

    def test_selector_prefix_ignored(self, sonarqube_check):
        check = sonarqube_check({'components': {'foo': {'include': ['sonarqube.foo.']}}})

        check.parse_config()
        _, selector = check._components['foo']

        assert selector('foo.bar')
        assert not selector('bar.baz')
