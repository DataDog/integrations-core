# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click
import requests
import re
import os
import zlib
import io
from pathlib import Path
import sys
import csv as csv_lib


VALID_PLATFORMS = ["linux-aarch64", "linux-x86_64", "macos-x86_64", "windows-x86_64"]
VALID_PYTHON_VERSIONS = ["3.12"]
REPO_PATH = Path(__file__).resolve().parents[5]



@click.command()
@click.option('--platform', type=click.Choice(VALID_PLATFORMS), help="Target platform")
@click.option('--python', 'version', type=click.Choice(VALID_PYTHON_VERSIONS), help="Python version (MAJOR.MINOR)")
@click.option('--compressed', is_flag=True, help="Measure compressed size")
@click.option('--csv', is_flag=True, help="Output in CSV format")
@click.pass_obj
def status(app, platform, version, compressed, csv):
    platforms = VALID_PLATFORMS if platform is None else [platform]
    versions = VALID_PYTHON_VERSIONS if version is None else [version]

    for i, (plat, ver) in enumerate([(p, v) for p in platforms for v in versions]):
        status_mode(app, plat, ver, compressed, csv, i)



def status_mode(app,platform, version, compressed,csv,i):
    if compressed:
        modules = get_compressed_files(app) + get_compressed_dependencies(app, platform,version)
        
        grouped_modules = group_modules(modules,platform, version)
        grouped_modules.sort(key=lambda x: x['Size (Bytes)'], reverse=True)
        
        if csv:
            headers = grouped_modules[0].keys()
            if i == 0:
                app.display(",".join(headers)) # comas alrededor

            for row in grouped_modules:
                app.display(",".join(str(row[h]) for h in headers))
        else:
            modules_table = {col: {} for col in grouped_modules[0].keys()}
            for i,row in enumerate(grouped_modules):
                for key,value in row.items():
                    modules_table[key][i] = str(value)
            app.display_table(platform + " " + version, modules_table)

    

def group_modules(modules, platform, version):
    grouped_aux = {}

    for file in modules:
        key = (file['Name'], file['Type'])
        grouped_aux[key] = grouped_aux.get(key, 0) + file["Size (Bytes)"]

    return [{'Name': name, 'Type': type, 'Size (Bytes)': size, 'Size': convert_size(size), 'Platform': platform, 'Version': version} for (name,type), size in grouped_aux.items()]


def get_compressed_files(app):
    #print("Getting compressed integrations")

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files(app)
    included_folder = "datadog_checks/"

    # script_path = 
    #REPO_PATH = os.path.abspath(os.path.join(os.path.abspath(__file__), "../../../../../../")) 

    file_data = []
    for root, _, files in os.walk(REPO_PATH):
        for file in files:
            file_path = os.path.join(root, file)

            # Convert the path to a relative format within the repo
            relative_path = os.path.relpath(file_path, REPO_PATH)

            # Filter files 
            if is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                try:
                    # Compress the file
                    compressor = zlib.compressobj()
                    compressed_size = 0

                    # original_size = os.path.getsize(file_path)
                    with open(file_path, "rb") as f:
                        while chunk := f.read(8192):  # Read in 8KB chunks
                            compressed_chunk = compressor.compress(chunk)
                            compressed_size += len(compressed_chunk)

                        compressed_size += len(compressor.flush())  # Flush the buffer
                    integration = relative_path.split("/")[0]
                    file_data.append({
                        "File Path": relative_path,
                        "Type": "Integration",
                        "Name": integration,
                        "Size (Bytes)": compressed_size
                    })

                except Exception as e:
                    app.display_error(f"Error processing {relative_path}: {e}") 
                    sys.exit(1) 

    return file_data
    

def get_compressed_dependencies(app,platform, version):
    #print("Getting compressed dependencies")

    #script_path = os.path.abspath(__file__)
    #REPO_PATH = os.path.abspath(os.path.join(script_path, "../../../../../../"))
    resolved_path = os.path.join(REPO_PATH, ".deps/resolved")

    if not os.path.exists(resolved_path) or not os.path.isdir(resolved_path):
        app.display_error(f"Error: Directory not found {resolved_path}")
        sys.exit(1)

    
    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)
        
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies(app, file_path)
            return get_dependencies_sizes(app, deps, download_urls)
    
    
    


def is_correct_dependency(platform, version, name):
    return platform in name and version in name
        
def get_dependencies_sizes(app, deps, download_urls):
    file_data = []
    for dep, url in zip(deps, download_urls):
        dep_response = requests.head(url)
        if dep_response.status_code != 200:
            app.display_error(f"Error {dep_response.status_code}: Unable to fetch the dependencies file")
            sys.exit(1)
        else:
            size = dep_response.headers.get("Content-Length", None)
            file_data.append({"File Path": dep, "Type": "Dependency", "Name": dep, "Size (Bytes)": int(size)})
        
    return file_data 


def get_dependencies(app,file_path):
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

def is_valid_integration(path, included_folder, ignored_files, git_ignore):
    # It is not an integration
    if path.startswith('.'):
        return False
    # It is part of an integration and it is not in the datadog_checks folder 
    elif not (included_folder in path):
        return False
    # It is an irrelevant file
    elif any(ignore in path for ignore in ignored_files):
        return False
    # This file is contained in .gitignore
    elif any(ignore in path for ignore in git_ignore):
        return False
    else:
        return True


def get_gitignore_files(app):
    #script_path = os.path.abspath(__file__)
    #repo_root = os.path.abspath(os.path.join(script_path, "../../../../../../")) 
    gitignore_path = os.path.join(REPO_PATH, ".gitignore")
    if not os.path.exists(gitignore_path):
        app.display_error(f"Error: .gitignore file not found at {gitignore_path}")
        sys.exit(1)
    
    try:
        with open(gitignore_path, "r", encoding="utf-8") as file:
            gitignore_content = file.read()
            ignored_patterns = [line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.startswith("#")]
            return ignored_patterns
    except Exception as e:
        app.display_error(f"Error reading .gitignore file: {e}")
        sys.exit(1)

def convert_size(size_bytes):
    #Transforms bytes into a human-friendly format (KB, MB, GB)
    for unit in [' B', ' KB', ' MB', ' GB']:
        if size_bytes < 1024:
            return (str(round(size_bytes, 2)) + unit)
        size_bytes /= 1024
    return (str(round(size_bytes, 2)) + " TB")


