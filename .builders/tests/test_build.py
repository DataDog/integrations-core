import subprocess
import sys
from pathlib import Path
import tempfile
import pytest
import mock


@pytest.mark.integration
def test_build_linux_x86_64():
    build_py = Path(__file__).parent.parent / 'build.py'
    image = 'linux-x86_64'
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"tmpdir: {tmpdir}")
        output_dir = Path(tmpdir) / 'output'
        worflow_id = '1234567890'
        # Run the build.py script as a subprocess
        result = subprocess.run([
            sys.executable, str(build_py), image, str(output_dir), '--workflow-id', worflow_id, 
        ], capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        assert result.returncode == 0, f"build.py failed: {result.stderr}"
        # Check that wheels/ and frozen.txt exist in the output directory
        wheels_dir = output_dir / 'wheels'
        frozen_txt = output_dir / 'frozen.txt'
        assert wheels_dir.is_dir(), f"Missing wheels directory: {wheels_dir}"
        assert frozen_txt.is_file(), f"Missing frozen.txt: {frozen_txt}"
        # Optionally, check that wheels/built and wheels/external exist
        assert (wheels_dir / 'built').is_dir(), "Missing built wheels directory"
        assert (wheels_dir / 'external').is_dir(), "Missing external wheels directory" 

        with open(frozen_txt, 'r') as f:
            frozen_lines = f.readlines()
            print(frozen_lines)
            assert len(frozen_lines) > 0, "Missing frozen lines"
            asserted_kafka = False
            for line in frozen_lines:
                if line.startswith('confluent-kafka'):
                    assert f'{worflow_id}WID' in line, "Missing workflow id in frozen.txt"
                    asserted_kafka = True
            assert asserted_kafka, "Missing confluent-kafka in frozen.txt"