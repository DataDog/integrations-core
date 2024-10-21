import os

SLURM_VERSION = '21.08.6'

def mock_output(filename):
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', filename)
    with open(fixture_path, 'r') as f:
        return f.read().strip()