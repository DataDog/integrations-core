# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.glusterfs import GlusterfsCheck
from datadog_checks.glusterfs.check import GSTATUS_PATH_SUFFIX

from .common import CHECK, E2E_INIT_CONFIG, EXPECTED_METRICS

pytestmark = pytest.mark.unit


def test_check(aggregator, instance, mock_gstatus_data):
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check(instance)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_parse_version(instance):
    c = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    major, minor, patch = c.parse_version('3.13.2')
    assert major == '3'
    assert minor == '13'
    assert patch == '2'


def test_init_derives_gstatus_path_from_run_path(datadog_agent):
    # Kills the AddNot/NumberReplacer/ReplaceUnaryOperator/ReplaceBinaryOperator mutants at
    # check.py:48-50 (stripping the trailing '/run' and appending GSTATUS_PATH_SUFFIX).
    datadog_agent._config['run_path'] = '/opt/datadog-agent/run'
    with mock.patch('datadog_checks.glusterfs.check.os.path.exists', return_value=True):
        check = GlusterfsCheck(CHECK, {}, [{'use_sudo': False}])
    assert check.gstatus_cmd == '/opt/datadog-agent' + GSTATUS_PATH_SUFFIX


def test_init_keeps_run_path_when_no_run_suffix(datadog_agent):
    # Kills the AddNot mutant at check.py:48 (path.endswith('/run') negation).
    datadog_agent._config['run_path'] = '/opt/datadog-agent'
    with mock.patch('datadog_checks.glusterfs.check.os.path.exists', return_value=True):
        check = GlusterfsCheck(CHECK, {}, [{'use_sudo': False}])
    assert check.gstatus_cmd == '/opt/datadog-agent' + GSTATUS_PATH_SUFFIX


def test_init_raises_when_gstatus_not_found(datadog_agent):
    # Kills the AddNot mutant at check.py:51 (os.path.exists negation).
    datadog_agent._config['run_path'] = '/opt/datadog-agent/run'
    with mock.patch('datadog_checks.glusterfs.check.os.path.exists', return_value=False):
        with pytest.raises(ConfigurationError):
            GlusterfsCheck(CHECK, {}, [{'use_sudo': False}])


def test_use_sudo_defaults_to_true():
    # Kills the ReplaceTrueWithFalse mutant at check.py:58 (use_sudo default value).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [{}])
    assert check.use_sudo is True


def test_get_gstatus_output_returns_captured_text(instance):
    # Kills the ReplaceTrueWithFalse mutants at check.py:61 (capture_output/text flags).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    stdout, stderr, returncode = check.get_gstatus_output('echo hello')
    assert stdout == 'hello\n'
    assert stderr == ''
    assert returncode == 0


def test_check_use_sudo_true_raises_when_sudo_returncode_positive(instance):
    # Kills ReplaceComparisonOperator_NotEq_{Eq,Lt,LtE} and NumberReplacer(!=1) mutants at check.py:68.
    inst = {'use_sudo': True}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=('{"data": {}}', '', 1),
    ):
        with pytest.raises(Exception, match='does not have sudo access'):
            check.check(inst)


def test_check_use_sudo_true_raises_when_sudo_returncode_negative(instance):
    # Kills ReplaceComparisonOperator_NotEq_{Gt,GtE} and NumberReplacer(!=-1) mutants at check.py:68.
    inst = {'use_sudo': True}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=('{"data": {}}', '', -1),
    ):
        with pytest.raises(Exception, match='does not have sudo access'):
            check.check(inst)


def test_check_use_sudo_true_raises_with_stderr_message_when_stdout_empty(instance):
    # Kills ReplaceOrWithAnd/ReplaceUnaryOperator_Delete_Not mutants at check.py:68, and the
    # ReplaceOrWithAnd mutant at check.py:69 (stderr-or-stdout fallback in the error message).
    inst = {'use_sudo': True}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=('', 'permission denied', 0),
    ):
        with pytest.raises(Exception, match='permission denied'):
            check.check(inst)


def test_check_use_sudo_false_skips_sudo_access_check(instance):
    # Kills the AddNot mutant at check.py:65 (self.use_sudo branch selection).
    inst = {'use_sudo': False}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=('{"data": {}}', 'boom', 1),
    ):
        check.check(inst)


def test_check_reports_json_decode_error_for_single_junk_line(instance, caplog):
    # Kills ReplaceUnaryOperator_USub_UAdd/_Delete_USub mutants at check.py:84 (split(...)[-1] index).
    inst = {'use_sudo': False}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=('not valid json and no newline', '', 0),
    ):
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(json.decoder.JSONDecodeError):
                check.check(inst)
    assert 'Unable to decode gstatus output' in caplog.text


def test_check_reports_json_decode_error_for_multiple_junk_lines(instance):
    # Kills the NumberReplacer mutant at check.py:84 (split maxsplit 1 -> 2).
    inst = {'use_sudo': False}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    stdout = 'junk line one\njunk line two\n{"data": {}}'
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=(stdout, '', 0),
    ):
        with pytest.raises(json.decoder.JSONDecodeError):
            check.check(inst)


def test_check_reports_generic_error_when_stdout_is_not_a_string(instance, caplog):
    # Kills the ExceptionReplacer mutant at check.py:89 (except Exception -> CosmicRayTestingException).
    inst = {'use_sudo': False}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=(None, '', 0),
    ):
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(AttributeError):
                check.check(inst)
    assert 'Encountered error trying to collect gluster status' in caplog.text


def test_check_no_cluster_service_check_when_status_missing(instance, aggregator):
    # Kills the AddNot mutant at check.py:102 (CLUSTER_STATUS presence check).
    inst = {'use_sudo': False}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=(json.dumps({'data': {}}), '', 0),
    ):
        check.check(inst)
    aggregator.assert_service_check('glusterfs.' + check.CLUSTER_SC, count=0)


@pytest.mark.parametrize(
    'status, expected_status, expected_message',
    [
        ('Healthy', AgentCheck.OK, None),
        ('Degraded', AgentCheck.CRITICAL, 'Cluster status is degraded'),
        ('Unreachable', AgentCheck.WARNING, 'Cluster status is unreachable'),
    ],
)
def test_check_cluster_service_check_reflects_status(instance, aggregator, status, expected_status, expected_message):
    # Kills ReplaceComparisonOperator_Eq_* mutants at check.py:104/106 and ReplaceBinaryOperator_Mod_*
    # mutants at check.py:108/112 (cluster status routing and message formatting).
    inst = {'use_sudo': False}
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [inst])
    with mock.patch(
        'datadog_checks.glusterfs.check.GlusterfsCheck.get_gstatus_output',
        return_value=(json.dumps({'data': {'cluster_status': status}}), '', 0),
    ):
        check.check(inst)
    sc_name = 'glusterfs.' + check.CLUSTER_SC
    if expected_message:
        aggregator.assert_service_check(sc_name, status=expected_status, message=expected_message)
    else:
        aggregator.assert_service_check(sc_name, status=expected_status)


def test_submit_version_metadata_noop_when_collection_disabled(instance, datadog_agent):
    # Kills the RemoveDecorator mutant at check.py:118 (@AgentCheck.metadata_entrypoint).
    datadog_agent._config['enable_metadata_collection'] = False
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check_id = 'test:123'
    check.submit_version_metadata({'glfs_version': '7.1'})
    datadog_agent.assert_metadata_count(0)


def test_submit_version_metadata_noop_when_version_missing(instance, datadog_agent, caplog):
    # Kills the ReplaceUnaryOperator_Delete_Not/AddNot mutants at check.py:121 (raw_version falsy check).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check_id = 'test:123'
    with caplog.at_level(logging.DEBUG):
        check.submit_version_metadata({})
    datadog_agent.assert_metadata_count(0)
    assert 'Could not retrieve GlusterFS version info' in caplog.text


def test_submit_version_metadata_includes_patch_when_present(instance, datadog_agent):
    # Kills the AddNot mutant at check.py:129 (patch truthiness check).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check_id = 'test:123'
    check.submit_version_metadata({'glfs_version': '7.1.2'})
    datadog_agent.assert_metadata(
        'test:123',
        {
            'version.raw': '7.1.2',
            'version.scheme': 'glusterfs',
            'version.major': '7',
            'version.minor': '1',
            'version.patch': '2',
        },
    )


def test_submit_version_metadata_excludes_patch_when_absent(instance, datadog_agent):
    # Kills the AddNot mutant at check.py:129 (patch truthiness check), inverse case.
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check_id = 'test:123'
    check.submit_version_metadata({'glfs_version': '7.1'})
    datadog_agent.assert_metadata_count(4)


def test_submit_version_metadata_swallows_unexpected_errors(instance, datadog_agent, caplog):
    # Kills the ExceptionReplacer mutant at check.py:132 (except Exception -> CosmicRayTestingException).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check_id = 'test:123'
    with caplog.at_level(logging.DEBUG):
        check.submit_version_metadata({'glfs_version': 'not.numeric'})
    datadog_agent.assert_metadata_count(0)
    assert 'Could not handle GlusterFS version' in caplog.text


def test_parse_version_two_part_leaves_patch_none(instance):
    # Kills the ReplaceComparisonOperator_Gt_GtE mutant at check.py:144 (len(split_version) > 2).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    assert check.parse_version('7.1') == ('7', '1', None)


def test_parse_version_invalid_format_is_swallowed(instance, caplog):
    # Kills the ExceptionReplacer mutant at check.py:146 (except ValueError -> CosmicRayTestingException).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    with caplog.at_level(logging.DEBUG):
        result = check.parse_version('noversion')
    assert result == (None, None, None)
    assert 'Unable to parse GlusterFS version' in caplog.text


def test_parse_volume_summary_emits_volume_service_check_when_health_present(instance, aggregator):
    # Kills the AddNot mutant at check.py:162 ('health' in volume presence check).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.parse_volume_summary([{'name': 'gv0', 'type': 'REPLICATE', 'health': 'up'}])
    aggregator.assert_service_check('glusterfs.' + check.VOLUME_SC, status=AgentCheck.OK, count=1)


def test_parse_volume_summary_skips_volume_service_check_when_health_absent(instance, aggregator):
    # Kills the AddNot mutant at check.py:162, inverse case.
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.parse_volume_summary([{'name': 'gv0', 'type': 'REPLICATE'}])
    aggregator.assert_service_check('glusterfs.' + check.VOLUME_SC, count=0)


def test_parse_subvols_stats_emits_brick_service_check_when_health_present(instance, aggregator):
    # Kills the AddNot mutant at check.py:170 ('health' in subvol presence check).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.parse_subvols_stats([{'name': 'sv0', 'health': 'up', 'bricks': []}], ['vol_name:gv0'])
    aggregator.assert_service_check('glusterfs.' + check.BRICK_SC, status=AgentCheck.OK, count=1)


def test_parse_subvols_stats_skips_brick_service_check_when_health_absent(instance, aggregator):
    # Kills the AddNot mutant at check.py:170, inverse case.
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.parse_subvols_stats([{'name': 'sv0', 'bricks': []}], ['vol_name:gv0'])
    aggregator.assert_service_check('glusterfs.' + check.BRICK_SC, count=0)


def test_parse_subvols_stats_brick_tags_split_server_and_export(instance, aggregator):
    # Kills the NumberReplacer mutants at check.py:175-176 (brick_name[0]/[1] index swaps).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    brick = {
        'name': 'server-a:/export/path',
        'type': 'Brick',
        'device': 'overlay',
        'fs_name': 'xfs',
        'block_size': '4096',
    }
    check.parse_subvols_stats([{'name': 'sv0', 'bricks': [brick]}], ['vol_name:gv0'])
    aggregator.assert_metric(
        'glusterfs.brick.block_size',
        tags=[
            'brick_server:server-a',
            'brick_export:/export/path',
            'type:Brick',
            'device:overlay',
            'fs_name:xfs',
            'vol_name:gv0',
            'subvol_name:sv0',
        ],
    )


def test_parse_healinfo_stats_only_processes_connected_bricks(instance, aggregator):
    # Kills ReplaceComparisonOperator_NotEq_Gt at check.py:192, ReplaceContinueWithBreak at
    # check.py:193, and NumberReplacer mutants at check.py:196-197 (brick_name index swaps).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    healinfo = [
        {'status': 'Aborted', 'name': 'node-a:/export-a', 'nr_entries': '9'},
        {'status': 'Connected', 'name': 'node-b:/export-b', 'nr_entries': '3'},
        {'status': 'Disconnected', 'name': 'node-c:/export-c', 'nr_entries': '5'},
    ]
    check.parse_healinfo_stats(healinfo, ['vol_name:gv0'])
    aggregator.assert_metric('glusterfs.heal_info.entries.count', count=1)
    aggregator.assert_metric(
        'glusterfs.heal_info.entries.count',
        tags=['brick_server:node-b', 'brick_export:/export-b', 'vol_name:gv0'],
    )


def test_submit_metrics_skips_na_values_and_continues_iteration(instance, aggregator):
    # Kills ReplaceComparisonOperator_Eq_{Gt,GtE,Is} mutants at check.py:214 and the
    # ReplaceContinueWithBreak mutant at check.py:215 (n/a values must be skipped, not abort the loop).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    payload = {'skip_me': 'N/A', 'keep_me': 42}
    mapping = {'skip_me': 'skip.metric', 'keep_me': 'keep.metric'}
    check.submit_metrics(payload, 'test', mapping, [])
    aggregator.assert_metric('glusterfs.test.skip.metric', count=0)
    aggregator.assert_metric('glusterfs.test.keep.metric', value=42)


def test_submit_metrics_parses_leading_numeric_component(instance, aggregator):
    # Kills the NumberReplacer mutants at check.py:220 (value_parsed[0] -> picking the unit instead
    # of the number).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    payload = {'v_size': '45.44 GiB'}
    mapping = {'v_size': 'size.total'}
    check.submit_metrics(payload, 'test', mapping, [])
    aggregator.assert_metric('glusterfs.test.size.total', value=45.44)


def test_submit_metrics_unparsable_value_is_skipped_and_iteration_continues(instance, aggregator):
    # Kills the ExceptionReplacer mutant at check.py:221 (except ValueError -> CosmicRayTestingException)
    # and the ReplaceContinueWithBreak mutant at check.py:223.
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    payload = {'v_size_used': 'bad value', 'online': 1}
    mapping = {'v_size_used': 'size.used', 'online': 'online'}
    check.submit_metrics(payload, 'test', mapping, [])
    aggregator.assert_metric('glusterfs.test.size.used', count=0)
    aggregator.assert_metric('glusterfs.test.online', value=1)


@pytest.mark.parametrize(
    'health, expected_status',
    [
        ('Up', AgentCheck.OK),
        ('Partial', AgentCheck.WARNING),
        ('Degraded', AgentCheck.CRITICAL),
        ('Down', AgentCheck.CRITICAL),
        ('Something else', AgentCheck.UNKNOWN),
    ],
)
def test_submit_service_check_maps_health_to_status(instance, aggregator, health, expected_status):
    # Kills ReplaceComparisonOperator_Eq_* mutants at check.py:231/233/235 and the ReplaceOrWithAnd
    # mutant at check.py:235 ('degraded' or 'down' must each independently route to CRITICAL).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.submit_service_check('test.sc', health, ['vol_name:gv0'])
    aggregator.assert_service_check('glusterfs.test.sc', status=expected_status, tags=['vol_name:gv0'])


def test_submit_service_check_message_includes_raw_value(instance, aggregator):
    # Kills the ReplaceBinaryOperator_Mod_* mutants at check.py:229 (message string formatting).
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.submit_service_check('test.sc', 'Partial', ['vol_name:gv0'])
    aggregator.assert_service_check('glusterfs.test.sc', message='Health in state: Partial')
