# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DOWNLOAD_SCRIPT = Path(__file__).parent / 'kind' / 'download-kubectl.sh'


@pytest.fixture
def download_env(tmp_path: Path) -> dict[str, str]:
    commands = tmp_path / 'bin'
    commands.mkdir()
    temporary_downloads = tmp_path / 'downloads'
    temporary_downloads.mkdir()
    timeout_binary = shutil.which('timeout')
    if timeout_binary is None:
        pytest.skip('GNU timeout is required for the kubectl fixture download')

    scripts = {
        'wget': '''import json
import os
import signal
import sys
import time
from pathlib import Path

log = Path(os.environ['MOCK_DOWNLOAD_LOG'])
previous_attempts = len(log.read_text().splitlines()) if log.exists() else 0
with log.open('a') as output:
    output.write(json.dumps(sys.argv[1:]) + '\\n')
statuses = json.loads(os.environ['MOCK_DOWNLOAD_STATUSES'])
status = statuses[min(previous_attempts, len(statuses) - 1)]
destination = next(arg.split('=', 1)[1] for arg in sys.argv if arg.startswith('--output-document='))
Path(destination).write_text('partial download' if status else 'kubectl fixture')
if os.environ.get('MOCK_HANG_DOWNLOAD'):
    if os.environ.get('MOCK_IGNORE_TERM'):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(10)
sys.exit(status)
''',
        'sleep': '''import os
import sys
from pathlib import Path

with Path(os.environ['MOCK_SLEEP_LOG']).open('a') as output:
    output.write(sys.argv[1] + '\\n')
''',
        'timeout': f'''import json
import os
import sys
from pathlib import Path

with Path(os.environ['MOCK_TIMEOUT_LOG']).open('a') as output:
    output.write(json.dumps(sys.argv[1:]) + '\\n')
args = sys.argv[1:]
if os.environ.get('MOCK_HANG_DOWNLOAD'):
    args[:2] = ['--kill-after=0.2s', '1s']
os.execv({timeout_binary!r}, [{timeout_binary!r}, *args])
''',
    }
    for name, source in scripts.items():
        command = commands / name
        command.write_text(f'#!{sys.executable}\n{source}')
        command.chmod(0o755)

    return {
        **os.environ,
        'PATH': f'{commands}{os.pathsep}{os.environ["PATH"]}',
        'TMPDIR': str(temporary_downloads),
        'MOCK_DOWNLOAD_STATUSES': '[0]',
        'MOCK_DOWNLOAD_LOG': str(tmp_path / 'wget.log'),
        'MOCK_SLEEP_LOG': str(tmp_path / 'sleep.log'),
        'MOCK_TIMEOUT_LOG': str(tmp_path / 'timeout.log'),
    }


@pytest.mark.parametrize(
    'statuses, expected_status, expected_attempts, expected_delays',
    [
        ([0], 0, 1, []),
        ([4, 0], 0, 2, [2]),
        ([4, 4, 4], 4, 3, [2, 4]),
        ([5], 5, 1, []),
        ([8], 8, 1, []),
    ],
    ids=['success', 'network-recovery', 'network-exhaustion', 'tls-failure', 'http-failure'],
)
def test_download_retry_policy(
    tmp_path: Path,
    download_env: dict[str, str],
    statuses: list[int],
    expected_status: int,
    expected_attempts: int,
    expected_delays: list[int],
):
    download_env['MOCK_DOWNLOAD_STATUSES'] = json.dumps(statuses)
    destination = tmp_path / 'kubectl'

    result = subprocess.run(
        ['sh', str(DOWNLOAD_SCRIPT), str(destination)],
        env=download_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == expected_status, result.stderr
    attempts = [json.loads(line) for line in Path(download_env['MOCK_DOWNLOAD_LOG']).read_text().splitlines()]
    assert len(attempts) == expected_attempts
    for args in attempts:
        assert '--no-verbose' in args
        assert '--timeout=15' in args
        assert '--tries=1' in args
    timeouts = [json.loads(line) for line in Path(download_env['MOCK_TIMEOUT_LOG']).read_text().splitlines()]
    assert all(args[:2] == ['--kill-after=5s', '60s'] for args in timeouts)
    sleep_log = Path(download_env['MOCK_SLEEP_LOG'])
    delays = [int(line) for line in sleep_log.read_text().splitlines()] if sleep_log.exists() else []
    assert delays == expected_delays
    assert f'attempt {expected_attempts}/3' in result.stderr
    if expected_status == 0:
        assert destination.read_text() == 'kubectl fixture'
    else:
        assert not destination.exists()
        assert 'failed' in result.stderr
    assert not list(Path(download_env['TMPDIR']).iterdir())


@pytest.mark.parametrize('ignore_term, expected_status', [(False, 124), (True, 137)])
def test_hung_download_is_bounded(
    tmp_path: Path, download_env: dict[str, str], ignore_term: bool, expected_status: int
):
    download_env['MOCK_HANG_DOWNLOAD'] = '1'
    if ignore_term:
        download_env['MOCK_IGNORE_TERM'] = '1'
    destination = tmp_path / 'kubectl'

    # Use the real timeout command with shortened deadlines, including the forced-kill path.
    result = subprocess.run(
        ['sh', str(DOWNLOAD_SCRIPT), str(destination)],
        env=download_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == expected_status, result.stderr
    assert len(Path(download_env['MOCK_DOWNLOAD_LOG']).read_text().splitlines()) == 3
    assert Path(download_env['MOCK_SLEEP_LOG']).read_text().splitlines() == ['2', '4']
    assert 'failed after 3 attempts' in result.stderr
    assert not destination.exists()
    assert not list(Path(download_env['TMPDIR']).iterdir())
