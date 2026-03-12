"""Add the scripts directory to sys.path so _release is importable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
