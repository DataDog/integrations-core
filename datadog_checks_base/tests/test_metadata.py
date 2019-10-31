# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import re
from collections import OrderedDict

import mock
import pytest

from datadog_checks.base import AgentCheck

pytestmark = pytest.mark.metadata

SET_CHECK_METADATA_METHOD = 'datadog_checks.base.stubs.datadog_agent.set_check_metadata'

# The order is used to derive the display name for the regex tests
NON_STANDARD_VERSIONS = OrderedDict()


class TestAttribute:
    def test_default(self):
        check = AgentCheck('test', {}, [{}])

        assert check._metadata_manager is None

    def test_no_check_id_error(self):
        check = AgentCheck('test', {}, [{}])

        with mock.patch('datadog_checks.base.checks.base.using_stub_aggregator', False):
            with pytest.raises(RuntimeError):
                check.set_metadata('foo', 'bar')


class TestRaw:
    def test_default(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('foo', 'bar')

            m.assert_called_once_with('test:123', 'foo', 'bar')

    def test_new_transformer(self):
        class NewAgentCheck(AgentCheck):
            METADATA_TRANSFORMERS = {'foo': lambda value, options: value[::-1]}

        check = NewAgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('foo', 'bar')

            m.assert_called_once_with('test:123', 'foo', 'rab')


class TestVersion:
    def test_override_allowed(self):
        class NewAgentCheck(AgentCheck):
            METADATA_TRANSFORMERS = {'version': lambda value, options: value[::-1]}

        check = NewAgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', 'bar')

            m.assert_called_once_with('test:123', 'version', 'rab')

    def test_unknown_scheme(self, caplog):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0.0', scheme='foo')

            assert m.call_count == 0

            expected_message = 'Unable to transform `version` metadata value `1.0.0`: Unsupported version scheme `foo`'
            for _, level, message in caplog.record_tuples:
                if level == logging.ERROR and message == expected_message:
                    break
            else:
                raise AssertionError('Expected ERROR log with message: {}'.format(expected_message))

    def test_semver_default(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0.5')

            m.assert_any_call('test:123', 'version.major', '1')
            m.assert_any_call('test:123', 'version.minor', '0')
            m.assert_any_call('test:123', 'version.patch', '5')
            m.assert_any_call('test:123', 'version.raw', '1.0.5')
            m.assert_any_call('test:123', 'version.scheme', 'semver')
            assert m.call_count == 5

    def test_semver_release(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0.5-gke.6', scheme='semver')

            m.assert_any_call('test:123', 'version.major', '1')
            m.assert_any_call('test:123', 'version.minor', '0')
            m.assert_any_call('test:123', 'version.patch', '5')
            m.assert_any_call('test:123', 'version.release', 'gke.6')
            m.assert_any_call('test:123', 'version.raw', '1.0.5-gke.6')
            m.assert_any_call('test:123', 'version.scheme', 'semver')
            assert m.call_count == 6

    def test_semver_release_and_build(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0.5-gke.6+3', scheme='semver')

            m.assert_any_call('test:123', 'version.major', '1')
            m.assert_any_call('test:123', 'version.minor', '0')
            m.assert_any_call('test:123', 'version.patch', '5')
            m.assert_any_call('test:123', 'version.release', 'gke.6')
            m.assert_any_call('test:123', 'version.build', '3')
            m.assert_any_call('test:123', 'version.raw', '1.0.5-gke.6+3')
            m.assert_any_call('test:123', 'version.scheme', 'semver')
            assert m.call_count == 7

    def test_semver_invalid(self, caplog):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0', scheme='semver')

            assert m.call_count == 0

            expected_prefix = 'Unable to transform `version` metadata value `1.0`: '
            for _, level, message in caplog.record_tuples:
                if level == logging.ERROR and message.startswith(expected_prefix):
                    break
            else:
                raise AssertionError('Expected ERROR log starting with message: {}'.format(expected_prefix))

    @pytest.mark.parametrize(
        'version, pattern, expected_parts',
        [
            (
                NON_STANDARD_VERSIONS.setdefault('Docker', '18.03.0-ce, build 0520e24'),
                r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)-(?P<release>\w+), build (?P<build>\w+)',
                {'major': '18', 'minor': '03', 'patch': '0', 'release': 'ce', 'build': '0520e24'},
            ),
            (
                NON_STANDARD_VERSIONS.setdefault('Exchange Server', '2007 SP3 8.3.83.006'),
                r'(?P<major>\d+) SP(?P<minor>\d+) (?P<build>[\w.]+)',
                {'major': '2007', 'minor': '3', 'build': '8.3.83.006'},
            ),
            (NON_STANDARD_VERSIONS.setdefault('Oracle', '19c'), r'(?P<major>\d+)\w*', {'major': '19'}),
            (
                NON_STANDARD_VERSIONS.setdefault('Presto', '0.221'),
                r'(?P<major>\d+).(?P<minor>\d+)',
                {'major': '0', 'minor': '221'},
            ),
            (
                NON_STANDARD_VERSIONS.setdefault('missing subgroup', '02'),
                r'(?P<major>\d+)(\.(?P<minor>\d+))?',
                {'major': '02'},
            ),
            (
                NON_STANDARD_VERSIONS.setdefault('precompiled', '1.2.3'),
                re.compile(r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'),
                {'major': '1', 'minor': '2', 'patch': '3'},
            ),
        ],
        ids=list(NON_STANDARD_VERSIONS),
    )
    def test_regex(self, version, pattern, expected_parts):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', version, scheme='regex', pattern=pattern)

            for name, value in expected_parts.items():
                m.assert_any_call('test:123', 'version.{}'.format(name), value)

            m.assert_any_call('test:123', 'version.raw', version)
            m.assert_any_call('test:123', 'version.scheme', 'test')
            assert m.call_count == len(expected_parts) + 2

    def test_regex_final_scheme(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata(
                'version',
                '1.2.3.beta',
                scheme='regex',
                final_scheme='semver',
                pattern=r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).(?P<release>\w+)',
            )

            m.assert_any_call('test:123', 'version.major', '1')
            m.assert_any_call('test:123', 'version.minor', '2')
            m.assert_any_call('test:123', 'version.patch', '3')
            m.assert_any_call('test:123', 'version.release', 'beta')
            m.assert_any_call('test:123', 'version.raw', '1.2.3.beta')
            m.assert_any_call('test:123', 'version.scheme', 'semver')
            assert m.call_count == 6

    def test_regex_no_pattern(self, caplog):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0', scheme='regex')

            assert m.call_count == 0

            expected_message = (
                'Unable to transform `version` metadata value `1.0`: Version scheme `regex` requires a `pattern` option'
            )
            for _, level, message in caplog.record_tuples:
                if level == logging.ERROR and message == expected_message:
                    break
            else:
                raise AssertionError('Expected ERROR log with message: {}'.format(expected_message))

    def test_regex_no_match(self, caplog):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0.0', scheme='regex', pattern='foo')

            assert m.call_count == 0

            expected_message = (
                'Unable to transform `version` metadata value `1.0.0`: '
                'Version does not match the regular expression pattern'
            )
            for _, level, message in caplog.record_tuples:
                if level == logging.ERROR and message == expected_message:
                    break
            else:
                raise AssertionError('Expected ERROR log with message: {}'.format(expected_message))

    def test_regex_no_subgroups(self, caplog):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0.0', scheme='regex', pattern=r'\d\.\d\.\d')

            assert m.call_count == 0

            expected_message = (
                'Unable to transform `version` metadata value `1.0.0`: '
                'Regular expression pattern has no named subgroups'
            )
            for _, level, message in caplog.record_tuples:
                if level == logging.ERROR and message == expected_message:
                    break
            else:
                raise AssertionError('Expected ERROR log with message: {}'.format(expected_message))

    def test_parts(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata(
                'version',
                '19.15.2.2',
                scheme='parts',
                part_map={'year': '19', 'major': '15', 'minor': '2', 'patch': '2', 'revision': '56789'},
            )

            m.assert_any_call('test:123', 'version.year', '19')
            m.assert_any_call('test:123', 'version.major', '15')
            m.assert_any_call('test:123', 'version.minor', '2')
            m.assert_any_call('test:123', 'version.patch', '2')
            m.assert_any_call('test:123', 'version.revision', '56789')
            m.assert_any_call('test:123', 'version.raw', '19.15.2.2')
            m.assert_any_call('test:123', 'version.scheme', 'test')
            assert m.call_count == 7

    def test_parts_final_scheme(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata(
                'version',
                '19.15.2.2',
                scheme='parts',
                final_scheme='calver',
                part_map={'year': '19', 'major': '15', 'minor': '2', 'patch': '2', 'revision': '56789'},
            )

            m.assert_any_call('test:123', 'version.year', '19')
            m.assert_any_call('test:123', 'version.major', '15')
            m.assert_any_call('test:123', 'version.minor', '2')
            m.assert_any_call('test:123', 'version.patch', '2')
            m.assert_any_call('test:123', 'version.revision', '56789')
            m.assert_any_call('test:123', 'version.raw', '19.15.2.2')
            m.assert_any_call('test:123', 'version.scheme', 'calver')
            assert m.call_count == 7

    def test_parts_no_part_map(self, caplog):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('version', '1.0', scheme='parts')

            assert m.call_count == 0

            expected_message = (
                'Unable to transform `version` metadata value `1.0`: '
                'Version scheme `parts` requires a `part_map` option'
            )
            for _, level, message in caplog.record_tuples:
                if level == logging.ERROR and message == expected_message:
                    break
            else:
                raise AssertionError('Expected ERROR log with message: {}'.format(expected_message))


class TestConfig:
    def test_no_section(self, caplog):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', {})

            assert m.call_count == 0

            expected_message = 'Unable to transform `config` metadata: The `section` option is required'
            for _, level, message in caplog.record_tuples:
                if level == logging.ERROR and message == expected_message:
                    break
            else:
                raise AssertionError('Expected ERROR log with message: {}'.format(expected_message))

    def test_non_primitive(self, caplog):
        check = AgentCheck('test', {}, [{'foo': ['bar']}])
        check.check_id = 'test:123'

        with caplog.at_level(logging.DEBUG), mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', check.instance, section='instance', whitelist=['foo'])

            assert m.call_count == 1

            args, _ = m.call_args
            assert args[0] == 'test:123'
            assert args[1] == 'config.instance'

            expected_message = (
                'Skipping metadata submission of non-primitive type `list` for field `foo` in section `instance`'
            )
            for _, level, message in caplog.record_tuples:
                if level == logging.WARNING and message == expected_message:
                    break
            else:
                raise AssertionError('Expected ERROR log with message: {}'.format(expected_message))

    def test_no_whitelist(self):
        check = AgentCheck('test', {}, [{'foo': 'bar'}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', check.instance, section='instance')

            assert m.call_count == 0

    def test_whitelist(self):
        check = AgentCheck('test', {}, [{'foo': 'bar'}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', check.instance, section='instance', whitelist=['foo'])

            assert m.call_count == 1

            args, _ = m.call_args
            assert args[0] == 'test:123'
            assert args[1] == 'config.instance'

            data = json.loads(args[2])[0]

            assert data.pop('is_set', None) is True
            assert data.pop('value', None) == 'bar'
            assert not data

    def test_whitelist_no_field(self):
        check = AgentCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', check.instance, section='instance', whitelist=['foo'])

            assert m.call_count == 1

            args, _ = m.call_args
            assert args[0] == 'test:123'
            assert args[1] == 'config.instance'

            data = json.loads(args[2])[0]

            assert data.pop('is_set', None) is False
            assert not data

    def test_blacklist(self):
        check = AgentCheck('test', {}, [{'product_pw': 'foo'}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', check.instance, section='instance', whitelist=['product_pw'], blacklist=['pw'])

            assert m.call_count == 0

    def test_blacklist_default(self):
        check = AgentCheck('test', {}, [{'product_password': 'foo'}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', check.instance, section='instance', whitelist=['product_password'])

            assert m.call_count == 0

    def test_whitelist_user_override(self):
        check = AgentCheck('test', {}, [{'foo': 'bar', 'bar': 'foo', 'metadata_whitelist': ['bar']}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata('config', check.instance, section='instance', whitelist=['foo', 'bar'])

            assert m.call_count == 1

            args, _ = m.call_args
            assert args[0] == 'test:123'
            assert args[1] == 'config.instance'

            data = json.loads(args[2])

            assert len(data) == 1
            data = data[0]

            assert data.pop('is_set', None) is True
            assert data.pop('value', None) == 'foo'
            assert not data

    def test_blacklist_user_override(self):
        check = AgentCheck('test', {}, [{'foo': 'bar', 'bar': 'foo', 'metadata_blacklist': ['bar']}])
        check.check_id = 'test:123'

        with mock.patch(SET_CHECK_METADATA_METHOD) as m:
            check.set_metadata(
                'config', check.instance, section='instance', whitelist=['foo', 'bar'], blacklist=['foo']
            )

            assert m.call_count == 1

            args, _ = m.call_args
            assert args[0] == 'test:123'
            assert args[1] == 'config.instance'

            data = json.loads(args[2])

            assert len(data) == 1
            data = data[0]

            assert data.pop('is_set', None) is True
            assert data.pop('value', None) == 'bar'
            assert not data
