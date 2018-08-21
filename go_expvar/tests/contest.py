import pytest
import mock



@pytest.fixture(scope="module")
def haproxy_mock():
    filepath = os.path.join(common.HERE, 'fixtures', 'mock_data')
    with open(filepath, 'r') as f:
        data = f.read()
    p = mock.patch('requests.get', return_value=mock.Mock(content=data))
    yield p.start()
    p.stop()


@pytest.fixture(scope="session")
def spin_up_go_expvar():
    
