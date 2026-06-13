# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

# We tell the server to not send the stack trace but
# the library leaves the start indication regardless.
STACK_TRACE_LEFTOVER = re.compile(r'\.?\s*Stack trace:\s*$')


class ErrorSanitizer(object):
    def __init__(self, password):
        self.password = password

    @staticmethod
    def clean(error):
        return STACK_TRACE_LEFTOVER.sub('', error)

    def scrub(self, error):
        if self.password:
            return error.replace(self.password, '**********')

        return error


def compact_query(query):
    return re.sub(r'\n\s+', ' ', query.strip())


def parse_version(version: str) -> list[int]:
    return [int(v) for v in version.split('.')]
