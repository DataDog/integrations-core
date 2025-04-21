# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import zlib
from datetime import date
from pathlib import Path
from types import TracebackType
from typing import Dict, List, Optional, Set, Tuple, Type, Union

import requests

from ddev.cli.application import Application


def valid_platforms_versions(repo_path: str) -> Tuple[Set[str], Set[str]]:
    resolved_path = os.path.join(repo_path, ".deps/resolved")
    platforms = []
    versions = []
    for file in os.listdir(resolved_path):
        platforms.append("_".join(file.split('_')[:-1]))
        match = re.search(r"\d+\.\d+", file)
        if match:
            versions.append(match.group())
    return set(platforms), set(versions)


def convert_size(size_bytes: float) -> str:
    for unit in [' B', ' KB', ' MB', ' GB']:
        if abs(size_bytes) < 1024:
            return str(round(size_bytes, 2)) + unit
        size_bytes /= 1024
    return str(round(size_bytes, 2)) + " TB"


def is_valid_integration(path: str, included_folder: str, ignored_files: Set[str], git_ignore: List[str]) -> bool:
    # It is not an integration
    if path.startswith('.'):
        return False
    # It is part of an integration and it is not in the datadog_checks folder
    elif included_folder not in path:
        return False
    # It is an irrelevant file
    elif any(ignore in path for ignore in ignored_files):
        return False
    # This file is contained in .gitignore
    elif any(ignore in path for ignore in git_ignore):
        return False
    else:
        return True


def is_correct_dependency(platform: str, version: str, name: str) -> bool:
    return platform in name and version in name


def print_csv(app: Application, i: Optional[int], modules: List[Dict[str, Union[str, int, date]]]) -> None:
    headers = [k for k in modules[0].keys() if k not in ['Size', 'Delta']]
    if not i:
        app.display(",".join(headers))

    for row in modules:
        if any(str(value).strip() not in ("", "0") for value in row.values()):
            app.display(",".join(format(str(row[h])) for h in headers))


def format(s: str) -> str:
    return f'"{s}"' if "," in s else s


def print_table(app: Application, mode: str, modules: List[Dict[str, Union[str, int, date]]]) -> None:
    modules_table: Dict[str, Dict[str, Union[str, int]]] = {
        col: {} for col in modules[0].keys() if '(Bytes)' not in col
    }
    for i, row in enumerate(modules):
        for key, value in row.items():
            if key in modules_table:
                modules_table[key][i] = str(value)
    app.display_table(mode, modules_table)


def get_dependencies_sizes(
    deps: List[str], download_urls: List[str], compressed: bool
) -> List[Dict[str, Union[str, int]]]:
    file_data = []
    for dep, url in zip(deps, download_urls, strict=False):
        if compressed:
            response = requests.head(url)
            response.raise_for_status()
            size_str = response.headers.get("Content-Length")
            if size_str is None:
                raise ValueError(f"Missing size for {dep}")
            size = int(size_str)

        else:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                wheel_data = response.content

            with tempfile.TemporaryDirectory() as tmpdir:
                wheel_path = Path(tmpdir) / "package.whl"
                with open(wheel_path, "wb") as f:
                    f.write(wheel_data)
                extract_path = Path(tmpdir) / "extracted"
                with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)

                size = 0
                for dirpath, _, filenames in os.walk(extract_path):
                    for name in filenames:
                        file_path = os.path.join(dirpath, name)
                        size += os.path.getsize(file_path)
        file_data.append({"File Path": dep, "Type": "Dependency", "Name": dep, "Size (Bytes)": int(size)})
    return file_data


def get_dependencies_list(file_path: str) -> Tuple[List[str], List[str]]:
    download_urls = []
    deps = []
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
        for line in file_content.splitlines():
            match = re.search(r"([\w\-\d\.]+) @ (https?://[^\s#]+)", line)
            if match:
                deps.append(match.group(1))
                download_urls.append(match.group(2))
            else:
                raise WrongDependencyFormat("The dependency format 'name @ link' is no longer supported.")

    return deps, download_urls


def group_modules(
    modules: List[Dict[str, Union[str, int]]], platform: str, version: str, i: Optional[int]
) -> List[Dict[str, Union[str, int]]]:
    if modules == []:
        return [
            {
                'Name': '',
                'Type': '',
                'Size (Bytes)': 0,
                'Size': '',
                'Platform': '',
                'Version': '',
            }
        ]
    grouped_aux: Dict[tuple[str, str], int] = {}
    for file in modules:
        key = (file['Name'], file['Type'])
        grouped_aux[key] = grouped_aux.get(key, 0) + file["Size (Bytes)"]
    if i is None:
        return [
            {'Name': name, 'Type': type, 'Size (Bytes)': size, 'Size': convert_size(size)}
            for (name, type), size in grouped_aux.items()
        ]
    else:
        return [
            {
                'Name': name,
                'Type': type,
                'Size (Bytes)': size,
                'Size': convert_size(size),
                'Platform': platform,
                'Version': version,
            }
            for (name, type), size in grouped_aux.items()
        ]


def get_gitignore_files(repo_path: str) -> List[str]:
    gitignore_path = os.path.join(repo_path, ".gitignore")
    with open(gitignore_path, "r", encoding="utf-8") as file:
        gitignore_content = file.read()
        ignored_patterns = [
            line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.startswith("#")
        ]
        return ignored_patterns


def compress(file_path: str) -> int:
    compressor = zlib.compressobj()
    compressed_size = 0
    # original_size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):  # Read in 8KB chunks
            compressed_chunk = compressor.compress(chunk)
            compressed_size += len(compressed_chunk)
        compressed_size += len(compressor.flush())
    return compressed_size


class WrongDependencyFormat(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)


class GitRepo:
    def __init__(self, url: Union[Path, str]) -> None:
        self.url = url
        self.repo_dir: str

    def __enter__(self):
        self.repo_dir = tempfile.mkdtemp()
        try:
            self._run("git status")
        except Exception:
            # If it is not already a repo
            self._run(f"git clone --quiet {self.url} {self.repo_dir}")
        return self

    def _run(self, command: str) -> List[str]:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, cwd=self.repo_dir)
        return result.stdout.strip().split('\n')

    def get_module_commits(
        self, module_path: str, initial: Optional[str], final: Optional[str], time: Optional[str]
    ) -> List[str]:
        self._run("git fetch origin --quiet")
        self._run("git checkout origin/HEAD")
        if time:
            return self._run(f'git log --since="{time}" --reverse --pretty=format:%H -- {module_path}')
        elif not initial and not final:
            return self._run(f"git log --reverse --pretty=format:%H -- {module_path}")
        elif not final:
            return self._run(f"git log --reverse --pretty=format:%H {initial}..HEAD -- {module_path}")
        else:
            try:
                self._run(f"git merge-base --is-ancestor {initial} {final}")
            except subprocess.CalledProcessError:
                raise ValueError(f"Commit {initial} does not come before {final}")
            return self._run(f"git log --reverse --pretty=format:%H {initial}..{final} -- {module_path}")

    def checkout_commit(self, commit: str) -> None:
        self._run(f"git fetch --quiet --depth 1 origin {commit}")
        self._run(f"git checkout --quiet {commit}")

    def sparse_checkout_commit(self, commit_sha: str, module: str) -> None:
        self._run("git sparse-checkout init --cone")
        self._run(f"git sparse-checkout set {module}")
        self._run(f"git checkout {commit_sha}")

    def get_commit_metadata(self, commit: str) -> Tuple[str, str, str]:
        result = self._run(f'git log -1 --date=format:"%b %d %Y" --pretty=format:"%ad\n%an\n%s" {commit}')
        date, author, message = result
        return date, author, message

    def get_creation_commit_module(self, module: str) -> str:
        return self._run(f'git log --reverse --format="%H" -- {module}')[0]

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        exception_traceback: Optional[TracebackType],
    ) -> None:
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
