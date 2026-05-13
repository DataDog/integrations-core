import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from process_analyze import Process, CollectedData, SkipEntry, ServiceVerdict, IntegrationResult


def test_imports():
    p = Process(pid=1, ppid=0, comm="nginx", cmdline="nginx", generated_name="nginx", has_service_data=True)
    assert p.pid == 1
