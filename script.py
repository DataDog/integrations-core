from pathlib import Path
from subprocess import call

from tqdm import tqdm

checks = [
    path for path in Path('.').iterdir()
    if path.is_dir() and not path.name.startswith(('.', '_')) and path.name != 'venv'
]

for check in tqdm(checks):
    command = ['isort', check]
    call(command)
