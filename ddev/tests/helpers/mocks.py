from collections.abc import Callable
from io import StringIO
from unittest.mock import MagicMock


class MockPopen:
    def __init__(
        self,
        returncode=0,
        side_effect: Callable | list[Callable] | None = None,
        stdout: bytes = b'',
        stderr: bytes = b'',
    ):
        self.returncode = returncode
        self.communicate = lambda *args, **kwargs: (stdout, stderr)
        self.stdout = StringIO(stdout.decode('utf-8'))
        self.kill = lambda: None
        self.side_effect = side_effect

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __getattr__(self, item):
        return MagicMock()
