# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
import sys

from ..common import ensure_bytes, to_native_string
from ..serialization import json
from .constants import KNOWN_DATADOG_AGENT_SETTER_METHODS, EnvVars


def run_with_isolation(check, aggregator, datadog_agent):
    message_indicator = os.urandom(8).hex()
    instance = dict(check.instance)
    init_config = dict(check.init_config)

    # Prevent fork bomb
    instance.pop('process_isolation', None)
    init_config.pop('process_isolation', None)

    env_vars = dict(os.environ)
    env_vars[EnvVars.MESSAGE_INDICATOR] = message_indicator
    env_vars[EnvVars.CHECK_NAME] = check.name
    env_vars[EnvVars.CHECK_ID] = check.check_id
    env_vars[EnvVars.INIT_CONFIG] = to_native_string(json.dumps(init_config))
    env_vars[EnvVars.INSTANCE] = to_native_string(json.dumps(instance))

    check_module = check.__module__
    check_class = check.__class__.__name__
    process = subprocess.Popen(
        [
            sys.executable,
            '-u',
            '-c',
            'from {check_module} import {check_class};'
            'from datadog_checks.base.utils.replay.redirect import run_check;'
            'run_check({check_class})'.format(check_module=check_module, check_class=check_class),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env_vars,
    )
    with process:
        check.log.info('Running check in a separate process')

        # To avoid blocking never use a pipe's file descriptor iterator. See https://bugs.python.org/issue3907
        for line in iter(process.stdout.readline, b''):
            line = line.rstrip().decode('utf-8')
            indicator, _, procedure = line.partition(':')
            if indicator != message_indicator:
                check.log.debug(line)
                continue

            check.log.trace(line)

            message_type, _, message = procedure.partition(':')
            message = json.loads(message)
            if message_type == 'aggregator':
                getattr(aggregator, message['method'])(check, *message['args'], **message['kwargs'])
            elif message_type == 'log':
                getattr(check.log, message['method'])(*message['args'])
            elif message_type == 'datadog_agent':
                method = message['method']
                value = getattr(datadog_agent, method)(*message['args'], **message['kwargs'])
                if method not in KNOWN_DATADOG_AGENT_SETTER_METHODS:
                    process.stdin.write(b'%s\n' % ensure_bytes(json.dumps({'value': value})))
                    process.stdin.flush()
            elif message_type == 'error':
                check.log.error(message[0]['traceback'])
                break
            else:
                check.log.error(
                    'Unknown message type encountered during communication with the isolated process: %s',
                    message_type,
                )
                break
