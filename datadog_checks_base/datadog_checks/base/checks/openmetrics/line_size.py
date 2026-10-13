# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import inspect
import weakref

# `iter_lines` keeps a line in memory until its end, so a response without line breaks would be read whole
MAX_LINE_SIZE = 4 * 1024 * 1024


def limit_line_size(response):
    """Make reading `response` fail once a line is longer than `MAX_LINE_SIZE` bytes, and return `response`."""
    raw = getattr(response, 'raw', None)
    # `requests` reads the decoded body through `raw.stream`. Test doubles without that method are left alone.
    if not inspect.ismethod(getattr(raw, 'stream', None)):
        return response
    # A weak reference, because `raw` -> `limited_stream` -> `raw.stream` -> `raw` would be a reference cycle
    stream = weakref.WeakMethod(raw.stream)

    def limited_stream(*args, **kwargs):
        line_size = 0  # Bytes since the last line break. A line can exceed the limit by up to one chunk.
        for chunk in stream()(*args, **kwargs):
            newline = chunk.rfind(b'\n')
            line_size = line_size + len(chunk) if newline < 0 else len(chunk) - newline - 1
            if line_size > MAX_LINE_SIZE:
                raise ValueError(f'Response contains a line longer than {MAX_LINE_SIZE} bytes')
            yield chunk

    raw.stream = limited_stream
    return response
