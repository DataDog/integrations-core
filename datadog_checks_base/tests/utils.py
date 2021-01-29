import platform

import pytest
from six import PY2

requires_windows = pytest.mark.skipif(platform.system() != 'Windows', reason='Test only valid on Windows')
requires_py3 = pytest.mark.skipif(PY2, reason='Test only available on Python 3')
