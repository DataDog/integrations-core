import pytest
from mock import patch

from datadog_checks.base.utils.hashing import HashMethod


@pytest.fixture(autouse=True)
def reset_hash_method():
    HashMethod._secure = None
    HashMethod._fast = None
    HashMethod._architecture = None


def test_hash_method_singleton():
    assert HashMethod.secure() is HashMethod.secure()
    assert HashMethod.fast() is HashMethod.fast()


def test_hash_method_secure():
    hasher = HashMethod.secure()
    h = hasher(b'test')
    # sha256 hash of 'test'
    assert h.hexdigest() == '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'


@patch('datadog_checks.base.utils.platform.Platform.python_architecture', return_value='64bit')
def test_hash_method_fast_64bit(mock_architecture):
    # Resetting the class variable to ensure the test is clean
    hasher = HashMethod.fast()
    h = hasher(b'test')
    # blake2b hash of 'test'
    from hashlib import blake2b

    assert h.hexdigest() == blake2b(b'test').hexdigest()


@patch('datadog_checks.base.utils.platform.Platform.python_architecture', return_value='32bit')
def test_hash_method_fast_32bit(mock_architecture):
    # Resetting the class variable to ensure the test is clean
    hasher = HashMethod.fast()
    h = hasher(b'test')
    # blake2s hash of 'test'
    from hashlib import blake2s

    assert h.hexdigest() == blake2s(b'test').hexdigest()


@patch('datadog_checks.base.utils.platform.Platform.python_architecture', return_value='64bit')
def test_hash_method_architecture_caching(mock_python_architecture):
    # First call, should call python_architecture
    arch = HashMethod.architecture()
    assert arch == '64bit'
    mock_python_architecture.assert_called_once()

    # Second call, should use cached value
    arch2 = HashMethod.architecture()
    assert arch2 == '64bit'
    mock_python_architecture.assert_called_once()  # still called once
