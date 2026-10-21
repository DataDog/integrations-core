# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.slurm import SlurmCheck
from datadog_checks.slurm.job_events import (
    SACCT_JOB_EVENT_FIELDS,
    SACCT_JOB_EVENT_IDS_PER_QUERY,
    SACCT_JOB_EVENT_PARAMS,
    SACCT_JOB_EVENT_WINDOW_OVERLAP,
    SacctJob,
    gpu_count,
    parse_sacct_time,
)

from .common import mock_output as mock_output_file

NOW = parse_sacct_time('2026-10-21T12:30:00')


def sacct_line(job_id, state, start='Unknown', end='Unknown', name='train', exit_code='0:0', **overrides):
    fields = {
        'JobIDRaw': job_id,
        'JobID': job_id,
        'Cluster': 'local',
        'User': 'alice',
        'Account': 'research',
        'Partition': 'gpu',
        'QOS': 'normal',
        'State': state,
        'ExitCode': exit_code,
        'Submit': '2026-10-21T12:00:00',
        'Start': start,
        'End': end,
        'NodeList': 'None assigned' if start in ('Unknown', 'None') else 'node1',
        'ReqTRES': 'billing=1,cpu=1,gres/gpu=2,mem=1G,node=1',
        'AllocTRES': '' if start in ('Unknown', 'None') else 'billing=2,cpu=2,gres/gpu=2,mem=2G,node=1',
        'JobName': name,
    }
    fields.update(overrides)
    return '|'.join(fields[field] for field in SACCT_JOB_EVENT_FIELDS)


def sacct_output(*lines):
    return '\n'.join(lines) + '\n'


@pytest.fixture
def gpu_monitoring_enabled(datadog_agent):
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': True}):
        yield


@pytest.fixture
def events_instance(instance):
    instance['collect_job_events'] = True
    return instance


def events_by_type(aggregator):
    return {(e['event_type'], e['aggregation_key']): e for e in aggregator.events}


def run_polls(check, *outputs, reasons=None):
    for i, output in enumerate(outputs):
        check._squeue_pending_reasons = reasons[i] if reasons else None
        check.process_job_events(check.parse_sacct_jobs(output), NOW)


class FakeSacct:
    """Answers the poll window query with `window` and ID queries from `by_id`, recording the IDs asked for."""

    def __init__(self):
        self.window = ''
        self.by_id = {}
        self.queried_ids = []
        self.fail_id_queries = False
        self.squeue = ''

    def __call__(self, cmd):
        if cmd[0].endswith('squeue'):
            return self.squeue, '', 0
        if not cmd[0].endswith('sacct') or '-anXP' not in cmd:
            return '', '', 0
        if '-j' not in cmd:
            return self.window, '', 0
        if self.fail_id_queries:
            return '', 'sacct: error: slurmdbd unreachable', 1
        ids = cmd[cmd.index('-j') + 1].split(',')
        self.queried_ids.append(ids)
        return sacct_output(*(line for job_id in ids for line in self.by_id.get(job_id, []))), '', 0


def poll(check, sacct, window='', by_id=None, reasons=None):
    sacct.window = window
    sacct.by_id = by_id or {}
    sacct.queried_ids = []
    check._squeue_pending_reasons = reasons
    with mock.patch('datadog_checks.slurm.check.get_subprocess_output', side_effect=sacct):
        check.collect_sacct_job_events()


@pytest.mark.parametrize(
    'collect_job_events, gpu_enabled, polled',
    [
        pytest.param(True, True, True, id='flag and gpu enabled'),
        pytest.param(True, False, False, id='gpu disabled'),
        pytest.param(False, True, False, id='flag disabled'),
    ],
)
@mock.patch('datadog_checks.slurm.check.get_subprocess_output')
def test_job_events_gated_by_gpu_monitoring(
    mock_output, instance, datadog_agent, dd_run_check, caplog, collect_job_events, gpu_enabled, polled
):
    mock_output.return_value = ('', '', 0)
    instance['collect_job_events'] = collect_job_events
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': gpu_enabled}):
        check = SlurmCheck('slurm', {}, [instance])
    dd_run_check(check)

    assert any('-anXP' in call.args[0] for call in mock_output.call_args_list) is polled
    assert ('requires GPU monitoring' in caplog.text) is (collect_job_events and not gpu_enabled)


@pytest.mark.usefixtures('gpu_monitoring_enabled')
@mock.patch('datadog_checks.slurm.check.get_subprocess_output')
def test_job_events_poll_window(mock_output, events_instance):
    check = SlurmCheck('slurm', {}, [events_instance])
    base_cmd = ['/usr/bin/sacct'] + SACCT_JOB_EVENT_PARAMS

    with mock.patch('datadog_checks.slurm.check.time.time', return_value=1000.0):
        mock_output.return_value = ('', '', 0)
        check.collect_sacct_job_events()
    mock_output.assert_called_with(base_cmd + [f'--starttime=now-{SACCT_JOB_EVENT_WINDOW_OVERLAP}seconds'])

    # A failed poll keeps the previous poll time so that the next window still covers it.
    with mock.patch('datadog_checks.slurm.check.time.time', return_value=1030.0):
        mock_output.return_value = ('', 'sacct: error: slurmdbd unreachable', 1)
        check.collect_sacct_job_events()
    with mock.patch('datadog_checks.slurm.check.time.time', return_value=1060.0):
        mock_output.return_value = ('', '', 0)
        check.collect_sacct_job_events()
    mock_output.assert_called_with(base_cmd + [f'--starttime=now-{SACCT_JOB_EVENT_WINDOW_OVERLAP + 60}seconds'])


@pytest.mark.usefixtures('gpu_monitoring_enabled')
@mock.patch('datadog_checks.slurm.check.get_subprocess_output')
def test_job_events_failed_poll_keeps_state(mock_output, events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])

    mock_output.return_value = (sacct_output(sacct_line('1', 'RUNNING', start='2026-10-21T12:01:00')), '', 0)
    check.collect_sacct_job_events()
    mock_output.return_value = ('', 'sacct: error: slurmdbd unreachable', 1)
    check.collect_sacct_job_events()
    mock_output.return_value = (
        sacct_output(sacct_line('1', 'COMPLETED', start='2026-10-21T12:01:00', end='2026-10-21T12:05:00')),
        '',
        0,
    )
    check.collect_sacct_job_events()

    assert [e['event_type'] for e in aggregator.events] == ['slurm.job.finished']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_first_poll_seeds_state(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    run_polls(check, sacct_output(sacct_line('1', 'PENDING'), sacct_line('2', 'RUNNING', start='2026-10-21T12:01:00')))

    assert aggregator.events == []


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_transitions(events_instance, aggregator):
    events_instance['tags'] = ['env:test']
    check = SlurmCheck('slurm', {}, [events_instance])
    run_polls(
        check,
        sacct_output(sacct_line('1', 'PENDING'), sacct_line('2', 'RUNNING', start='2026-10-21T12:01:00')),
        sacct_output(
            sacct_line('1', 'RUNNING', start='2026-10-21T12:10:00'),
            sacct_line('2', 'COMPLETED', start='2026-10-21T12:01:00', end='2026-10-21T12:20:00'),
            sacct_line(
                '3', 'FAILED', start='2026-10-21T12:21:00', end='2026-10-21T12:22:00', exit_code='3:0', name='short'
            ),
        ),
    )

    events = events_by_type(aggregator)
    assert sorted(events) == [
        ('slurm.job.finished', 'slurm_job:local:2'),
        ('slurm.job.finished', 'slurm_job:local:3'),
        ('slurm.job.started', 'slurm_job:local:1'),
        ('slurm.job.started', 'slurm_job:local:3'),
        ('slurm.job.submitted', 'slurm_job:local:3'),
    ]

    started = events[('slurm.job.started', 'slurm_job:local:1')]
    assert started['alert_type'] == 'info'
    assert started['timestamp'] == int(parse_sacct_time('2026-10-21T12:10:00'))
    assert started['msg_title'] == 'Slurm job 1 (train) started'
    assert 'Queued wait time was 600s.' in started['msg_text']
    assert sorted(started['tags']) == sorted(
        [
            'env:test',
            'slurm_job_id:1',
            'slurm_job_name:train',
            'slurm_job_user:alice',
            'slurm_job_account:research',
            'slurm_partition_name:gpu',
            'slurm_job_qos:normal',
            'slurm_cluster_name:local',
            'slurm_job_state:RUNNING',
            'slurm_job_transition:started',
            'slurm_job_gpu_count:2',
            'slurm_job_node_list:node1',
        ]
    )

    completed = events[('slurm.job.finished', 'slurm_job:local:2')]
    assert completed['alert_type'] == 'success'
    assert completed['msg_title'] == 'Slurm job 2 (train) finished: COMPLETED'
    assert 'Run time was 1140s.' in completed['msg_text']

    failed = events[('slurm.job.finished', 'slurm_job:local:3')]
    assert failed['alert_type'] == 'error'
    assert 'slurm_job_exitcode:3:0' in failed['tags']

    submitted = events[('slurm.job.submitted', 'slurm_job:local:3')]
    assert submitted['timestamp'] == int(parse_sacct_time('2026-10-21T12:00:00'))
    assert 'slurm_job_state:PENDING' in submitted['tags']
    assert not any(tag.startswith('slurm_job_node_list:') for tag in submitted['tags'])
    assert 'slurm_job_state:RUNNING' in events[('slurm.job.started', 'slurm_job:local:3')]['tags']
    assert 'slurm_job_state:FAILED' in failed['tags']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_no_duplicates(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    running = sacct_output(sacct_line('1', 'RUNNING', start='2026-10-21T12:01:00'))
    run_polls(check, '', running, running, running)

    assert [e['event_type'] for e in aggregator.events] == ['slurm.job.submitted', 'slurm.job.started']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_requeue(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    run_polls(
        check,
        sacct_output(sacct_line('1', 'RUNNING', start='2026-10-21T12:01:00')),
        sacct_output(sacct_line('1', 'REQUEUED', start='2026-10-21T12:01:00', end='2026-10-21T12:05:00')),
        sacct_output(sacct_line('1', 'RUNNING', start='2026-10-21T12:08:00')),
    )

    assert [(e['event_type'], e['alert_type']) for e in aggregator.events] == [
        ('slurm.job.requeued', 'warning'),
        ('slurm.job.started', 'info'),
    ]


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_cancelled_while_pending(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    run_polls(
        check,
        sacct_output(sacct_line('1', 'PENDING')),
        sacct_output(sacct_line('1', 'CANCELLED by 1001', start='None', end='2026-10-21T12:05:00')),
    )

    [event] = aggregator.events
    assert event['event_type'] == 'slurm.job.finished'
    assert event['alert_type'] == 'warning'
    assert event['msg_title'] == 'Slurm job 1 (train) finished: CANCELLED'
    assert 'State detail: CANCELLED by 1001.' in event['msg_text']
    assert 'slurm_job_state:CANCELLED' in event['tags']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_submitted_carries_pending_reason(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    run_polls(check, '', sacct_output(sacct_line('1', 'PENDING')), reasons=[{}, {'1': 'Priority'}])

    [event] = aggregator.events
    assert event['event_type'] == 'slurm.job.submitted'
    assert 'slurm_job_reason:Priority' in event['tags']
    assert 'Pending reason is Priority.' in event['msg_text']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_pending_reason_changes(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    pending = sacct_output(sacct_line('1', 'PENDING'))
    run_polls(
        check,
        *[pending] * 7,
        reasons=[
            {'1': 'None'},
            {'1': 'Priority'},
            {'1': 'Priority'},
            {'1': 'QOSMaxGRESPerUser'},
            # squeue produced nothing: the reason is kept, so it is not reported again afterwards.
            None,
            {'1': 'QOSMaxGRESPerUser'},
            {'1': 'None'},
        ],
    )

    assert [(e['msg_title'], e['alert_type']) for e in aggregator.events] == [
        ('Slurm job 1 (train) pending: Priority', 'info'),
        ('Slurm job 1 (train) pending: QOSMaxGRESPerUser', 'warning'),
    ]
    event = aggregator.events[-1]
    assert event['event_type'] == 'slurm.job.pending'
    assert event['timestamp'] == int(NOW)
    assert 'slurm_job_reason:QOSMaxGRESPerUser' in event['tags']
    assert 'slurm_job_state:PENDING' in event['tags']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_pending_reason_from_squeue_run(events_instance, aggregator, dd_run_check):
    events_instance['collect_squeue_stats'] = True
    check = SlurmCheck('slurm', {}, [events_instance])
    sacct = FakeSacct()
    sacct.window = sacct_output(sacct_line('45', 'PENDING'))

    with mock.patch('datadog_checks.slurm.check.get_subprocess_output', side_effect=sacct):
        sacct.squeue = '45|root|train|PENDING||1|(Priority)|gres/gpu:2|gpu\n'
        dd_run_check(check)
        sacct.squeue = mock_output_file('squeue.txt')
        dd_run_check(check)

    [event] = aggregator.events
    assert event['msg_title'] == 'Slurm job 45 (train) pending: Resources'


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_held_job_queried_by_id(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    sacct = FakeSacct()
    pending = [sacct_line('1', 'PENDING')]

    poll(check, sacct, window=sacct_output(*pending), reasons={'1': 'Resources'})
    # Holding the job removes it from the time window.
    poll(check, sacct, by_id={'1': pending}, reasons={'1': 'JobHeldUser'})
    assert sacct.queried_ids == [['1']]
    poll(
        check,
        sacct,
        by_id={'1': [sacct_line('1', 'CANCELLED by 1001', start='None', end='2026-10-21T12:05:00')]},
    )

    assert [(e['msg_title'], e['alert_type']) for e in aggregator.events] == [
        ('Slurm job 1 (train) pending: JobHeldUser', 'warning'),
        ('Slurm job 1 (train) finished: CANCELLED', 'warning'),
    ]

    # Finished jobs are no longer queried.
    poll(check, sacct)
    assert sacct.queried_ids == []


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_pending_jobs_discovered_from_squeue(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    sacct = FakeSacct()

    poll(check, sacct, reasons={})
    poll(check, sacct, by_id={'5': [sacct_line('5', 'PENDING')]}, reasons={'5': 'Dependency'})

    [event] = aggregator.events
    assert event['msg_title'] == 'Slurm job 5 (train) submitted'
    assert 'slurm_job_reason:Dependency' in event['tags']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_id_query_ignores_unrequested_array_tasks(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    sacct = FakeSacct()
    finished_task = sacct_line('20', 'COMPLETED', start='2026-10-21T10:00:00', end='2026-10-21T10:01:00', JobID='19_1')

    poll(check, sacct, reasons={})
    poll(
        check,
        sacct,
        by_id={'19': [sacct_line('19', 'PENDING', JobID='19_[2-3]'), finished_task]},
        reasons={'19': 'JobHeldUser'},
    )

    assert [e['msg_title'] for e in aggregator.events] == ['Slurm job 19_[2-3] (train) submitted']


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_id_queries_are_batched(events_instance):
    check = SlurmCheck('slurm', {}, [events_instance])
    sacct = FakeSacct()

    poll(check, sacct, reasons={str(i): 'Dependency' for i in range(SACCT_JOB_EVENT_IDS_PER_QUERY + 1)})

    assert [len(ids) for ids in sacct.queried_ids] == [SACCT_JOB_EVENT_IDS_PER_QUERY, 1]


@pytest.mark.usefixtures('gpu_monitoring_enabled')
def test_job_events_failed_id_query_keeps_state(events_instance, aggregator):
    check = SlurmCheck('slurm', {}, [events_instance])
    sacct = FakeSacct()
    pending = [sacct_line('1', 'PENDING')]

    poll(check, sacct, window=sacct_output(*pending))
    sacct.fail_id_queries = True
    poll(check, sacct)
    sacct.fail_id_queries = False
    # Had the failed poll replaced the state, the job would be reported as newly submitted.
    poll(check, sacct, window=sacct_output(*pending))

    assert aggregator.events == []


def test_sacct_job_line_with_pipe_in_job_name():
    job = SacctJob.from_sacct_line(sacct_line('1', 'PENDING', name='a|b'))

    assert job.name == 'a|b'
    assert job.state == 'PENDING'


def test_sacct_job_line_with_missing_fields():
    assert SacctJob.from_sacct_line('1|1|local') is None


@pytest.mark.parametrize(
    'tres, expected',
    [
        ('billing=1,cpu=1,mem=1G,node=1', 0),
        ('billing=2,cpu=2,gres/gpu=1,mem=2G,node=1', 1),
        ('cpu=8,gres/gpu:a100=4,gres/gpu=4,node=1', 4),
        ('cpu=8,gres/gpu:a100=4,node=1', 4),
        ('', 0),
    ],
)
def test_gpu_count(tres, expected):
    assert gpu_count(tres) == expected
