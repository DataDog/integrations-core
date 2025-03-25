# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
import re
import requests
import os
import zlib

#utilities

#mirar si existe
def convert_size(size_bytes):
    # Transforms bytes into a human-friendly format (KB, MB, GB)
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
    headers = modules[0].keys()
    if i == 0:
        app.display(",".join(headers))  

    for row in modules:
        app.display(",".join(format(str(row[h])) for h in headers))

def format(s):
    if "," in s:
        return '"' + s + '"'
    else:
        return s
    
def print_table(app, modules, platform, version):
    modules_table = {col: {} for col in modules[0].keys()}
    for i, row in enumerate(modules):
        for key, value in row.items():
            modules_table[key][i] = str(value)
    app.display_table(platform + " " + version, modules_table)
    
def get_dependencies_sizes(app, deps, download_urls):
    file_data = []
    for dep, url in zip(deps, download_urls, strict=False):
        dep_response = requests.head(url)
        if dep_response.status_code != 200:
            app.display_error(f"Error {dep_response.status_code}: Unable to fetch the dependencies file")
            sys.exit(1)
        else:
            size = dep_response.headers.get("Content-Length", None)
            file_data.append({"File Path": dep, "Type": "Dependency", "Name": dep, "Size (Bytes)": int(size)})

    return file_data

def get_dependencies(app, file_path):
    download_urls = []
    deps = []
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
            for line in file_content.splitlines():
                match = re.search(r"([\w\-\d\.]+) @ (https?://[^\s#]+)", line)
                if match:
                    deps.append(match.group(1))
                    download_urls.append(match.group(2))
    except Exception as e:
        app.display_error(f"Error reading file {file_path}: {e}")
        sys.exit(1)

    return deps, download_urls


def group_modules(modules, platform, version):
    grouped_aux = {}

    for file in modules:
        key = (file['Name'], file['Type'])
        grouped_aux[key] = grouped_aux.get(key, 0) + file["Size (Bytes)"]

    return [
        {
            'Name': name ,
            'Type': type ,
            'Size (Bytes)': size ,
            'Size': convert_size(size),
            'Platform': platform ,
            'Version': version ,
        }
        for (name, type), size in grouped_aux.items()
    ]

def get_gitignore_files(app, repo_path):
    gitignore_path = os.path.join(repo_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        app.display_error(f"Error: .gitignore file not found at {gitignore_path}")
        sys.exit(1)

    try:
        with open(gitignore_path, "r", encoding="utf-8") as file:
            gitignore_content = file.read()
            ignored_patterns = [
                line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.startswith("#")
            ]
            return ignored_patterns
    except Exception as e:
        app.display_error(f"Error reading .gitignore file: {e}")
        sys.exit(1)

def compress(app, file_path, relative_path):
    compressor = zlib.compressobj()
    compressed_size = 0
    try:
        # original_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):  # Read in 8KB chunks
                compressed_chunk = compressor.compress(chunk)
                compressed_size += len(compressed_chunk)

            compressed_size += len(compressor.flush()) 
        return compressed_size
    except Exception as e:
        app.display_error(f"Error processing {relative_path}: {e}")
        sys.exit(1)