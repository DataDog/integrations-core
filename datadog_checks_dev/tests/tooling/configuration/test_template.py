# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest

from datadog_checks.dev import TempDir
from datadog_checks.dev.fs import ensure_parent_dir_exists, path_join, write_file
from datadog_checks.dev.tooling.configuration.template import ConfigTemplates


class TestLoadBasic:
    def test_default(self):
        templates = ConfigTemplates()

        assert templates.load('init_config/tags') == {
            'name': 'tags',
            'value': {
                'example': ['<KEY_1>:<VALUE_1>', '<KEY_2>:<VALUE_2>'],
                'type': 'array',
                'items': {'type': 'string'},
            },
            'description': (
                'A list of tags to attach to every metric and service check emitted by this integration.\n'
                '\n'
                'Learn more about tagging at https://docs.datadoghq.com/tagging\n'
            ),
        }

    def test_custom_path_precedence(self):
        with TempDir() as d:
            template_file = path_join(d, 'init_config', 'tags.yaml')
            ensure_parent_dir_exists(template_file)
            write_file(template_file, 'test:\n- foo\n- bar')

            templates = ConfigTemplates([d])

            assert templates.load('init_config/tags') == {'test': ['foo', 'bar']}

    def test_cache(self):
        with TempDir() as d:
            template_file = path_join(d, 'init_config', 'tags.yaml')
            ensure_parent_dir_exists(template_file)
            write_file(template_file, 'test:\n- foo\n- bar')

            templates = ConfigTemplates([d])
            templates.load('init_config/tags')
            write_file(template_file, '> invalid')

            assert templates.load('init_config/tags') == {'test': ['foo', 'bar']}

    def test_unknown_template(self):
        templates = ConfigTemplates()

        with pytest.raises(ValueError, match='^Template `unknown` does not exist$'):
            templates.load('unknown')

    def test_parse_error(self):
        with TempDir() as d:
            template_file = path_join(d, 'invalid.yaml')
            ensure_parent_dir_exists(template_file)
            write_file(template_file, '> invalid')

            templates = ConfigTemplates([d])

            with pytest.raises(ValueError, match='^Unable to parse template `{}`'.format(re.escape(template_file))):
                templates.load('invalid')


class TestLoadBranches:
    def test_mapping(self):
        templates = ConfigTemplates()

        assert templates.load('init_config/tags.value.example') == ['<KEY_1>:<VALUE_1>', '<KEY_2>:<VALUE_2>']

    def test_mapping_not_found(self):
        templates = ConfigTemplates()

        with pytest.raises(ValueError, match='^Template `init_config/tags` has no element `value.foo`$'):
            templates.load('init_config/tags.value.foo')

    def test_list(self):
        templates = ConfigTemplates()

        assert templates.load('instances/http.skip_proxy.value') == {'example': False, 'type': 'boolean'}

    def test_list_not_found(self):
        templates = ConfigTemplates()

        with pytest.raises(ValueError, match='^Template `instances/http` has no named element `foo`$'):
            templates.load('instances/http.foo')

    def test_primitive(self):
        templates = ConfigTemplates()

        assert templates.load('instances/http.skip_proxy.value.example') is False

    def test_primitive_recurse(self):
        templates = ConfigTemplates()

        with pytest.raises(
            ValueError,
            match=(
                '^Template `instances/http.skip_proxy.value.example` does '
                'not refer to a mapping, rather it is type `bool`$'
            ),
        ):
            templates.load('instances/http.skip_proxy.value.example.foo')


class TestApplyOverrides:
    def test_mapping(self):
        templates = ConfigTemplates()

        template = templates.load('init_config/tags')
        errors = templates.apply_overrides(template, {'value.example': ['foo', 'bar']})
        assert not errors

        assert template == {
            'name': 'tags',
            'value': {'example': ['foo', 'bar'], 'type': 'array', 'items': {'type': 'string'}},
            'description': (
                'A list of tags to attach to every metric and service check emitted by this integration.\n'
                '\n'
                'Learn more about tagging at https://docs.datadoghq.com/tagging\n'
            ),
        }

    def test_mapping_with_branches(self):
        templates = ConfigTemplates()

        template = templates.load('init_config/tags.value')
        errors = templates.apply_overrides(template, {'example': ['foo', 'bar']})
        assert not errors

        assert template == {'example': ['foo', 'bar'], 'type': 'array', 'items': {'type': 'string'}}

    def test_mapping_with_name(self):
        templates = ConfigTemplates()

        template = templates.load('instances/tags')
        overrides = {'tags.required': True}
        templates.apply_overrides(template, overrides)
        assert not overrides

        assert template.get('required') is True

    def test_list(self):
        templates = ConfigTemplates()

        template = templates.load('instances/http')
        errors = templates.apply_overrides(template, {'skip_proxy.description': 'foobar'})
        assert not errors

        assert {
            'name': 'skip_proxy',
            'value': {'example': False, 'type': 'boolean'},
            'description': 'foobar',
        } in template

    def test_list_with_branches(self):
        templates = ConfigTemplates()

        template = templates.load('instances/http.skip_proxy')
        errors = templates.apply_overrides(template, {'description': 'foobar'})
        assert not errors

        assert template == {
            'name': 'skip_proxy',
            'value': {'example': False, 'type': 'boolean'},
            'description': 'foobar',
        }

    def test_list_replace(self):
        templates = ConfigTemplates()

        original_template = templates.load('instances/http')
        index = next(i for i, item in enumerate(original_template) if item.get('name') == 'skip_proxy')  # no cov

        template = templates.load('instances/http')
        errors = templates.apply_overrides(template, {'skip_proxy': 'foobar'})
        assert not errors

        assert 'foobar' in template
        assert template.index('foobar') == index
        template.remove('foobar')

        for item in template:
            assert item.get('name') != 'skip_proxy'

    def test_list_not_found(self):
        templates = ConfigTemplates()

        template = templates.load('instances/http')
        errors = templates.apply_overrides(template, {'proxy.value.properties.foo.foo': 'bar'})

        assert len(errors) == 1
        assert errors[0] == 'Template override `proxy.value.properties` has no named mapping `foo`'

    def test_list_not_found_root(self):
        templates = ConfigTemplates()

        template = templates.load('instances/http')
        errors = templates.apply_overrides(template, {'foo': 'bar'})

        assert len(errors) == 1
        assert errors[0] == 'Template override has no named mapping `foo`'

    def test_primitive(self):
        templates = ConfigTemplates()

        template = templates.load('instances/http')
        errors = templates.apply_overrides(template, {'proxy.description.foo': 'bar'})

        assert len(errors) == 1
        assert errors[0] == 'Template override `proxy.description` does not refer to a mapping'

    def test_primitive_recurse(self):
        templates = ConfigTemplates()

        template = templates.load('instances/http')
        errors = templates.apply_overrides(template, {'proxy.description.foo.foo': 'bar'})

        assert len(errors) == 1
        assert errors[0] == 'Template override `proxy.description` does not refer to a mapping'
