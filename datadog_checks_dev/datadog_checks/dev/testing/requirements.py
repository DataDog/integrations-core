import pytest
from datadog_checks.dev.testing.utils import ON_WINDOWS, ON_MACOS
from six import PY2


requires_windows = pytest.mark.skipif(not ON_WINDOWS, reason='Requires Windows')
requires_linux = pytest.mark.skipif(ON_MACOS or ON_WINDOWS, reason='Requires Linux')
requires_unix = pytest.mark.skipif(ON_WINDOWS, reason='Requires Linux or macOS')

requires_py3 = pytest.mark.skipif(PY2, reason='Test only available on Python 3')
