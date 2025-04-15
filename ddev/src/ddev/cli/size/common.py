# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
import zlib
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path
import zipfile


def valid_platforms_versions(repo_path):
    resolved_path = os.path.join(repo_path, ".deps/resolved")
    platforms = []
    versions = []
    for file in os.listdir(resolved_path):
        platforms.append("_".join(file.split('_')[:-1]))
        match = re.search(r"\d+\.\d+", file)
        if match:
            versions.append(match.group())
    return set(platforms), set(versions)
    

# mirar si existe
def convert_size(size_bytes):
    for unit in [' B', ' KB', ' MB', ' GB']:
        if size_bytes < 1024:
            return str(round(size_bytes, 2)) + unit
        size_bytes /= 1024
    return str(round(size_bytes, 2)) + " TB"


def is_valid_integration(path, included_folder, ignored_files, git_ignore):
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


def is_correct_dependency(platform, version, name):
    return platform in name and version in name


def print_csv(app, i, modules):
    headers = [k for k in modules[0].keys() if k not in ['Size', 'Delta']]
    if not i:
        app.display(",".join(headers))

    for row in modules:
        app.display(",".join(format(str(row[h])) for h in headers))


def format(s):
    if "," in s:
        return '"' + s + '"'
    else:
        return s


def print_table(app, mode, modules):
    modules_table = {col: {} for col in modules[0].keys() if '(Bytes)' not in col}
    for i, row in enumerate(modules):
        for key, value in row.items():
            if key in modules_table:
                modules_table[key][i] = str(value)
    app.display_table(mode, modules_table)


def get_dependencies_sizes(deps, download_urls, compressed):
    file_data = []
    for dep, url in zip(deps, download_urls, strict=False):
        if compressed:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                size = int(response.headers.get("Content-Length"))
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


def get_dependencies_list(file_path):
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


def group_modules(modules, platform, version, i):
    grouped_aux = {}

    for file in modules:
        key = (file['Name'], file['Type'])
        grouped_aux[key] = grouped_aux.get(key, 0) + file["Size (Bytes)"]
    if i is None:
        return [
        {
            'Name': name,
            'Type': type,
            'Size (Bytes)': size,
            'Size': convert_size(size)
        }
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


def get_gitignore_files(repo_path):
    gitignore_path = os.path.join(repo_path, ".gitignore")
    with open(gitignore_path, "r", encoding="utf-8") as file:
        gitignore_content = file.read()
        ignored_patterns = [
            line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.startswith("#")
        ]
        return ignored_patterns


def compress(file_path):
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
    def __init__(self, mensaje):
        super().__init__(mensaje)

class GitRepo:
    def __init__(self, url):
        self.url = url
        self.repo_dir = None

    def __enter__(self):
        self.repo_dir = tempfile.mkdtemp()
        try:
            self._run("git status")
        except Exception:
            # If it is not already a repo
            self._run(f"git clone --quiet {self.url} {self.repo_dir}")
        return self

    def _run(self, command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, cwd=self.repo_dir)
        return result.stdout.strip().split('\n')

    def get_module_commits(self, module_path, initial, final, time):
        self._run("git fetch origin --quiet") # 1 min no coger todo solo el module
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
           

    def checkout_commit(self, commit):
        self._run(f"git fetch --quiet --depth 1 origin {commit}")
        self._run(f"git checkout --quiet {commit}")

    def sparse_checkout_commit(self, commit_sha, module):
        self._run("git sparse-checkout init --cone") 
        self._run(f"git sparse-checkout set {module}")
        self._run(f"git checkout {commit_sha}")
    
    def get_commit_metadata(self,commit):
        result = self._run(f'git log -1 --date=format:"%b %d %Y" --pretty=format:"%ad\n%an\n%s" {commit}')
        date, author, message = result
        return date, author, message
    
    def get_creation_commit_module(self, module):
        return self._run(f'git log --reverse --format="%H" -- {module}')[0]

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
