# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import socket
import time
from contextlib import closing
from typing import Callable, Dict, List, Tuple, Union  # noqa: F401

from six import string_types
from six.moves.urllib.request import urlopen

from .errors import RetryError
from .structures import LazyFunction
from .subprocess import run_command
from .utils import file_exists


class WaitFor(LazyFunction):
    def __init__(
        self,
        func,  # type: Callable
        attempts=60,  # type: int
        wait=1,  # type: int
        args=(),  # type: Tuple
        kwargs=None,  # type: Dict
    ):
        if kwargs is None:
            kwargs = {}

        self.func = func
        self.attempts = attempts
        self.wait = wait
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        last_result = None
        last_error = None

        for _ in range(self.attempts):
            try:
                result = self.func(*self.args, **self.kwargs)
            except Exception as e:
                last_error = str(e)
                time.sleep(self.wait)
                continue
            else:
                last_result = result

            if last_result is None or last_result is True:
                return True

            time.sleep(self.wait)
        else:
            raise RetryError(
                'Result: {}\nError: {}\nFunction: {}, Args: {}, Kwargs: {}\n'.format(
                    repr(last_result), last_error, self.func.__name__, self.args, self.kwargs
                )
            )


class CheckEndpoints(LazyFunction):
    def __init__(
        self,
        endpoints,  # type: Union[str, List[str]]
        timeout=1,  # type: int
        attempts=60,  # type: int
        wait=1,  # type: int
    ):
        self.endpoints = [endpoints] if isinstance(endpoints, string_types) else endpoints
        self.timeout = timeout
        self.attempts = attempts
        self.wait = wait

    def __call__(self):
        last_endpoint = ''
        last_error = None

        for _ in range(self.attempts):
            for endpoint in self.endpoints:
                last_endpoint = endpoint
                try:
                    request = urlopen(endpoint, timeout=self.timeout)
                except Exception as e:
                    last_error = str(e)
                    break
                else:
                    status_code = request.getcode()
                    if 400 <= status_code < 600:
                        last_error = 'status {}'.format(status_code)
                        break
            else:
                break

            time.sleep(self.wait)
        else:
            raise RetryError('Endpoint: {}\n' 'Error: {}'.format(last_endpoint, last_error))


class CheckCommandOutput(LazyFunction):
    def __init__(
        self,
        command,  # type: Union[str, List[str]]
        patterns,  # type: Union[str, List[str]]
        matches=1,  # type: Union[str, int]  #Either 'all' or a number
        stdout=True,  # type: bool
        stderr=True,  # type: bool
        attempts=60,  # type: int
        wait=1,  # type: int
    ):
        """
        Checks if the provided patterns are present in the output of a command

        :param command: The command to run
        :param patterns: List of patterns to match
        :param matches: How many of the provided patterns need to match, it can be a number or "all"
        :param stdout: Whether to search for the provided patterns in stdout
        :param stderr: Whether to search for the provided patterns in stderr
        :param attempts: How many times to try searching for the patterns
        :param wait: How long, in seconds, to wait between attempts
        """
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.attempts = attempts
        self.wait = wait

        if not (self.stdout or self.stderr):
            raise ValueError('Must capture stdout, stderr, or both.')

        if isinstance(patterns, string_types):
            patterns = [patterns]

        self.patterns = [
            re.compile(pattern, re.M) if isinstance(pattern, string_types) else pattern for pattern in patterns
        ]

        if matches == 'all':
            self.matches = len(patterns)
        else:
            self.matches = int(matches)

    def __call__(self):
        log_output = ''
        exit_code = 0

        for _ in range(self.attempts):
            result = run_command(self.command, capture=True)
            exit_code = result.code

            if self.stdout and self.stderr:
                log_output = result.stdout + result.stderr
            elif self.stdout:
                log_output = result.stdout
            else:
                log_output = result.stderr

            matches = 0
            missing_patterns = set(self.patterns)
            for pattern in self.patterns:
                if pattern.search(log_output):
                    matches += 1
                    missing_patterns.remove(pattern)

            if matches >= self.matches:
                return matches

            time.sleep(self.wait)
        else:
            patterns = '\t- '.join([''] + [str(p) for p in self.patterns])
            missing_patterns = '\t- '.join([''] + [str(p) for p in missing_patterns])
            raise RetryError(
                u'Command: {}\nFailed to match `{}` of the patterns.\n'
                u'Provided patterns: {}\n'
                u'Missing patterns: {}\n'
                u'Exit code: {}\n'
                u'Captured Output: {}'.format(
                    self.command, self.matches, patterns, missing_patterns, exit_code, log_output
                )
            )


class CheckDockerLogs(CheckCommandOutput):
    def __init__(
        self,
        identifier,  # type: str
        patterns,  # type: Union[str, List[str]]
        matches=1,  # type: Union[str, int]
        stdout=True,  # type: bool
        stderr=True,  # type: bool
        attempts=60,  # type: int
        wait=1,  # type: int
    ):
        """
        Checks if the provided patterns are present in docker logs

        :param identifier: The docker image identifier
        :param patterns: List of patterns to match
        :param matches: How many of the provided patterns need to match, it can be a number or "all"
        :param stdout: Whether to search for the provided patterns in stdout
        :param stderr: Whether to search for the provided patterns in stderr
        :param attempts: How many times to try searching for the patterns
        :param wait: How long, in seconds, to wait between attempts
        """
        if file_exists(identifier):
            command = ['docker', 'compose', '-f', identifier, 'logs']
        else:
            command = ['docker', 'logs', identifier]

        super(CheckDockerLogs, self).__init__(
            command, patterns, matches=matches, stdout=stdout, stderr=stderr, attempts=attempts, wait=wait
        )
        self.identifier = identifier


class WaitForPortListening(WaitFor):
    """Wait until a server is available on `host:port`."""

    def __init__(
        self,
        host,  # type: str
        port,  # type: int
        attempts=60,  # type: int
        wait=1,  # type: int
    ):
        super(WaitForPortListening, self).__init__(self.connect, attempts, wait, args=(host, port))

    def connect(self, host, port):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.connect((host, port))
