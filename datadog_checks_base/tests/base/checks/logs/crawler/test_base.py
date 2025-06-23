# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.logs.crawler.base import LogCrawlerCheck
from datadog_checks.base.checks.logs.crawler.stream import LogRecord, LogStream


def test_submission(dd_run_check, datadog_agent):
    class TestLogStream(LogStream):
        def __init__(self, start, **kwargs):
            super().__init__(**kwargs)

            self.start = start

        def records(self, cursor=None):
            start = cursor['counter'] + 1 if cursor is not None else self.start
            for i in range(start, start + 2):
                message = f'{self.name} {i}'
                data = (
                    {'message': message}
                    if i % 2 == 0
                    else {'message': message, 'ddtags': self.construct_tags([f'{self.name}:tag{i}'])}
                )
                yield LogRecord(data, cursor={'counter': i})

    class TestLogCrawlerCheck(LogCrawlerCheck):
        def get_log_streams(self):
            return iter(
                [
                    TestLogStream(start=2, check=self, name='stream1'),
                    TestLogStream(start=6, check=self, name='stream2'),
                ]
            )

    check = TestLogCrawlerCheck('test', {}, [{'tags': ['foo:bar', 'baz:qux']}])
    check.check_id = 'test'

    for _ in range(2):
        dd_run_check(check)

    datadog_agent.assert_logs(
        check.check_id,
        [
            {'message': 'stream1 2', 'ddtags': 'baz:qux,foo:bar'},
            {'message': 'stream1 3', 'ddtags': 'baz:qux,foo:bar,stream1:tag3'},
            {'message': 'stream2 6', 'ddtags': 'baz:qux,foo:bar'},
            {'message': 'stream2 7', 'ddtags': 'baz:qux,foo:bar,stream2:tag7'},
            {'message': 'stream1 4', 'ddtags': 'baz:qux,foo:bar'},
            {'message': 'stream1 5', 'ddtags': 'baz:qux,foo:bar,stream1:tag5'},
            {'message': 'stream2 8', 'ddtags': 'baz:qux,foo:bar'},
            {'message': 'stream2 9', 'ddtags': 'baz:qux,foo:bar,stream2:tag9'},
        ],
    )
