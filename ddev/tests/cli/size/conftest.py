import pytest
import pytest_mock


@pytest.fixture(autouse=True)
def mock_matplotlib_globally(mocker: pytest_mock.MockerFixture):
    # We are not validating whether matplotlib is beting executed, we should mock it entirely
    mocker.patch("matplotlib.pyplot.show")
    mocker.patch("matplotlib.pyplot.savefig")
    mocker.patch("matplotlib.pyplot.figure")
