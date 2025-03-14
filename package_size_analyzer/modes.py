import requests
import pandas as pd
import re
import os
from tabulate import tabulate
import zlib
import io


def status_mode(platform, version, compressed):
    if compressed:
        df1 = pd.DataFrame(get_compressed_files())
        print("Compressed integrations done")

        df2 = pd.DataFrame(get_compressed_dependencies(platform,version))
        print("Compressed dependencies done")
        

        df = pd.concat([df1, df2], ignore_index=True)
        
        # Calculate the size for the whole module
        df_grouped = df.groupby(["Name", 'Type'], as_index=False).agg({"Size (Bytes)": "sum"})
        df_grouped = df_grouped.sort_values(by="Size (Bytes)", ascending=False).reset_index(drop=True)
        

        df_grouped["Size"] = df_grouped["Size (Bytes)"].apply(convert_size)
        df_grouped.to_csv("compressed_status_" + platform + "_" + version + ".csv", index=False)
        df.to_csv("compressed_status_all_" + platform + "_" + version + ".csv", index=False)
        df_grouped = df_grouped.drop(columns=['Size (Bytes)'])
        print('--------------', platform,version,'--------------')
        print(tabulate(df_grouped, headers='keys', tablefmt='grid'))
        print("CSV exported")




def get_compressed_files():
    print("Getting compressed integrations")

    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    git_ignore = get_gitignore_files()
    included_folder = "datadog_checks/"

    script_path = os.path.abspath(__file__)
    parent_dir = os.path.dirname(script_path)
    repo_path = os.path.dirname(parent_dir)

    file_data = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)

            # Convert the path to a relative format within the repo
            relative_path = os.path.relpath(file_path, repo_path)

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
                    print(f"Error processing {relative_path}: {e}")  

    return file_data
    

def get_compressed_dependencies(platform=None, version=None):
    print("Getting compressed dependencies")

    script_path = os.path.abspath(__file__)
    parent_dir = os.path.dirname(script_path)
    repo_path = os.path.dirname(parent_dir)
    resolved_path = os.path.join(repo_path, ".deps/resolved")

    if not os.path.exists(resolved_path) or not os.path.isdir(resolved_path):
        print(f"Error: Directory not found {resolved_path}")
        return []

    file_data = []
    
    for filename in os.listdir(resolved_path):
        file_path = os.path.join(resolved_path, filename)
        
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            deps, download_urls = get_dependencies(file_path)
            return get_dependencies_sizes(deps, download_urls)
    
    
    


def is_correct_dependency(platform, version, name):
    return platform in name and version in name
        
def get_dependencies_sizes(deps, download_urls):
    file_data = []
    for dep, url in zip(deps, download_urls):
        dep_response = requests.head(url)
        if dep_response.status_code != 200:
            print(f"Error {response.status_code}: Unable to fetch the dependencies file")
        else:
            size = dep_response.headers.get("Content-Length", None)
            file_data.append({"File Path": dep, "Type": "Dependency", "Name": dep, "Size (Bytes)": int(size)})
        
    return file_data 


def get_dependencies(file_path):
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
        print(f"Error reading file {file_path}: {e}")
    
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


def get_gitignore_files():
    script_path = os.path.abspath(__file__)
    parent_dir = os.path.dirname(script_path)
    repo_path = os.path.dirname(parent_dir)
    gitignore_path = os.path.join(repo_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        print(f"Error: .gitignore file not found at {gitignore_path}")
        return []
    
    try:
        with open(gitignore_path, "r", encoding="utf-8") as file:
            gitignore_content = file.read()
            ignored_patterns = [line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.startswith("#")]
            return ignored_patterns
    except Exception as e:
        print(f"Error reading .gitignore file: {e}")
        return []

def convert_size(size_bytes):
    """Transforms bytes into a human-friendly format (KB, MB, GB) with 3 decimal places."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return (str(round(size_bytes, 2)) + unit)
        size_bytes /= 1024
    return (str(round(size_bytes, 2)) + "TB")


