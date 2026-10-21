# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import time
from dataclasses import dataclass

# JobName goes last so that a '|' inside a job name cannot shift the other fields.
SACCT_JOB_EVENT_FIELDS = [
    'JobIDRaw',
    'JobID',
    'Cluster',
    'User',
    'Account',
    'Partition',
    'QOS',
    'State',
    'ExitCode',
    'Submit',
    'Start',
    'End',
    'NodeList',
    'ReqTRES',
    'AllocTRES',
    'JobName',
]

# -a: all users, -X: job allocations only (no steps), -n: no header, -P: '|' separated without a trailing '|'.
SACCT_JOB_EVENT_PARAMS = ['-anXP', '-o', ','.join(SACCT_JOB_EVENT_FIELDS)]

# The poll window reaches back past the previous poll so that job updates slurmctld sends to slurmdbd
# after that poll are not missed. Already seen transitions are deduplicated against the stored state.
SACCT_JOB_EVENT_WINDOW_OVERLAP = 60

# Jobs missing from the poll window are queried by ID in batches, to keep the command line short.
SACCT_JOB_EVENT_IDS_PER_QUERY = 500

SACCT_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

TERMINAL_STATES = frozenset(
    {
        'BOOT_FAIL',
        'CANCELLED',
        'COMPLETED',
        'DEADLINE',
        'FAILED',
        'NODE_FAIL',
        'OUT_OF_MEMORY',
        'TIMEOUT',
    }
)

# States after which a job missing from the poll window is no longer queried by ID. A preempted job that is
# requeued shows up again in the window or in squeue.
SACCT_JOB_EVENT_DONE_STATES = TERMINAL_STATES | {'PREEMPTED'}

STATE_TRANSITIONS = {
    **dict.fromkeys(TERMINAL_STATES, 'finished'),
    'PREEMPTED': 'preempted',
    'REQUEUED': 'requeued',
    'REQUEUE_FED': 'requeued',
    'REQUEUE_HOLD': 'requeued',
    'SPECIAL_EXIT': 'requeued',
    'SUSPENDED': 'suspended',
}

TRANSITION_ALERT_TYPES = {
    'submitted': 'info',
    'started': 'info',
    'preempted': 'warning',
    'requeued': 'warning',
    'suspended': 'warning',
}

FINISHED_ALERT_TYPES = {
    'COMPLETED': 'success',
    'CANCELLED': 'warning',
}

# Pending reasons that are part of normal scheduling. Any other reason, such as a QOS or association limit or an
# unavailable node, means the job cannot run until something changes and is reported as a warning.
EXPECTED_PENDING_REASONS = frozenset({'BeginTime', 'Dependency', 'Priority', 'Resources'})

NO_PENDING_REASON = 'None'

GPU_TRES_RE = re.compile(r'(?:^|,)gres/gpu(?::[^=,]+)?=(\d+)')


def parse_sacct_time(value: str) -> float | None:
    # sacct prints 'Unknown' or 'None' for times that have not happened yet. Times are in the local timezone.
    try:
        return time.mktime(time.strptime(value, SACCT_TIME_FORMAT))
    except ValueError:
        return None


def gpu_count(tres: str) -> int:
    # Typed and untyped GPUs are both listed ('gres/gpu=2,gres/gpu:a100=2'); the untyped entry is the total.
    counts = [int(count) for count in GPU_TRES_RE.findall(tres)]
    return max(counts, default=0)


@dataclass(frozen=True)
class SacctJob:
    key: str
    job_id_raw: str
    job_id: str
    cluster: str
    user: str
    account: str
    partition: str
    qos: str
    state: str
    state_detail: str
    exit_code: str
    submit: float | None
    start: float | None
    end: float | None
    node_list: str
    req_tres: str
    alloc_tres: str
    name: str

    @classmethod
    def from_sacct_line(cls, line: str) -> SacctJob | None:
        fields = line.split('|', len(SACCT_JOB_EVENT_FIELDS) - 1)
        if len(fields) != len(SACCT_JOB_EVENT_FIELDS):
            return None

        (
            job_id_raw,
            job_id,
            cluster,
            user,
            account,
            partition,
            qos,
            state,
            exit_code,
            submit,
            start,
            end,
            node_list,
            req_tres,
            alloc_tres,
            name,
        ) = fields
        # States can carry a detail, such as 'CANCELLED by 1001'.
        state_name, _, state_detail = state.strip().partition(' ')

        return cls(
            key=f'{cluster}:{job_id_raw}',
            job_id_raw=job_id_raw,
            job_id=job_id,
            cluster=cluster,
            user=user,
            account=account,
            partition=partition,
            qos=qos,
            state=state_name.upper(),
            state_detail=state_detail,
            exit_code=exit_code,
            submit=parse_sacct_time(submit),
            start=parse_sacct_time(start),
            end=parse_sacct_time(end),
            node_list=node_list,
            req_tres=req_tres,
            alloc_tres=alloc_tres,
            name=name,
        )

    @property
    def gpus(self) -> int:
        return gpu_count(self.alloc_tres) or gpu_count(self.req_tres)


def job_transitions(previous: SacctJob | None, current: SacctJob) -> list[str]:
    """Return the transitions `current` went through since `previous`, in the order they happened.

    A job that is submitted and finishes between two polls is only seen once, so all of its
    transitions are derived from that single record. A requeued job keeps its ID and gets a new
    start time when it runs again, which is reported as a new start.
    """
    transitions = []
    if previous is None:
        transitions.append('submitted')

    if current.start is not None and (previous is None or previous.start != current.start):
        transitions.append('started')

    state_transition = STATE_TRANSITIONS.get(current.state)
    if state_transition and (previous is None or previous.state != current.state):
        transitions.append(state_transition)

    return transitions


def transition_alert_type(transition: str, job: SacctJob, pending_reason: str | None = None) -> str:
    if transition == 'finished':
        return FINISHED_ALERT_TYPES.get(job.state, 'error')
    if transition == 'pending':
        return 'info' if pending_reason in EXPECTED_PENDING_REASONS else 'warning'
    return TRANSITION_ALERT_TYPES.get(transition, 'info')


def transition_timestamp(transition: str, job: SacctJob, now: float) -> float:
    if transition == 'submitted':
        timestamp = job.submit
    elif transition == 'started':
        timestamp = job.start
    elif transition in ('pending', 'suspended'):
        timestamp = None
    else:
        timestamp = job.end
    return timestamp if timestamp is not None else now


def job_event_title(transition: str, job: SacctJob, pending_reason: str | None = None) -> str:
    if transition == 'finished':
        label = f'finished: {job.state}'
    elif transition == 'pending':
        label = f'pending: {pending_reason}'
    else:
        label = transition
    return f'Slurm job {job.job_id} ({job.name}) {label}'


def job_event_text(transition: str, job: SacctJob, pending_reason: str | None = None) -> str:
    parts = [f'Slurm job {job.job_id} ({job.name}) of user {job.user} in partition {job.partition}']

    if transition == 'submitted':
        parts.append(f'was submitted requesting {job.req_tres or "no TRES"}.')
        if pending_reason:
            parts.append(f'Pending reason is {pending_reason}.')
    elif transition == 'pending':
        parts.append(f'is pending with reason {pending_reason}.')
    elif transition == 'started':
        parts.append(f'started on {job.node_list} with {job.alloc_tres or "no TRES"}.')
        if job.submit is not None and job.start is not None:
            parts.append(f'Queued wait time was {job.start - job.submit:.0f}s.')
    elif transition == 'finished':
        parts.append(f'finished with state {job.state} and exit code {job.exit_code}.')
        if job.start is not None and job.end is not None:
            parts.append(f'Run time was {job.end - job.start:.0f}s.')
    else:
        parts.append(f'was {transition}.')

    if job.state_detail:
        parts.append(f'State detail: {job.state} {job.state_detail}.')

    return ' '.join(parts)


def transition_state(transition: str, job: SacctJob) -> str:
    # A single sacct record can yield several transitions, so earlier ones must not report the latest state.
    if transition in ('submitted', 'pending'):
        return 'PENDING'
    if transition == 'started':
        return 'RUNNING'
    return job.state


def job_event_tags(
    transition: str, job: SacctJob, base_tags: list[str], pending_reason: str | None = None
) -> list[str]:
    tags = list(base_tags)
    tags.extend(
        [
            f'slurm_job_id:{job.job_id}',
            f'slurm_job_name:{job.name or "null"}',
            f'slurm_job_user:{job.user or "null"}',
            f'slurm_job_account:{job.account or "null"}',
            f'slurm_partition_name:{job.partition or "null"}',
            f'slurm_job_qos:{job.qos or "null"}',
            f'slurm_cluster_name:{job.cluster or "null"}',
            f'slurm_job_state:{transition_state(transition, job)}',
            f'slurm_job_transition:{transition}',
        ]
    )

    if job.gpus:
        tags.append(f'slurm_job_gpu_count:{job.gpus}')
    if pending_reason:
        tags.append(f'slurm_job_reason:{pending_reason}')
    if transition not in ('submitted', 'pending') and job.node_list and job.node_list != 'None assigned':
        tags.append(f'slurm_job_node_list:{job.node_list}')
    if transition == 'finished':
        tags.append(f'slurm_job_exitcode:{job.exit_code}')

    return tags
