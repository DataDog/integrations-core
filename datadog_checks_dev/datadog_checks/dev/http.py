# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from io import BytesIO
from textwrap import dedent

from requests import Response


class MockResponse(Response):
    def __init__(self, content='', file_path=None, status_code=200, normalize_content=True):
        super(MockResponse, self).__init__()

        if file_path is not None:
            with open(file_path, 'rb') as f:
                self.raw = BytesIO(f.read())
        else:
            # For multi-line string literals
            if normalize_content:
                content = dedent(content[1:])

            self.raw = BytesIO(content.encode('utf-8'))

        self.status_code = status_code
