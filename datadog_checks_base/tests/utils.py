
import platform
import pytest

requires_windows = pytest.mark.skipif(
    platform.system() != 'Windows', reason="Test only valid on Windows"
)
