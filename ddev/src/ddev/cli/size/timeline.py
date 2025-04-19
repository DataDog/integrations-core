
import click
import requests
import os
import re
from datetime import datetime
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
import tempfile
from pathlib import Path
import zipfile
from .common import (
    compress,
    get_gitignore_files,
    convert_size,
    is_correct_dependency,
    is_valid_integration,
    print_csv,
    print_table,
    GitRepo,
    WrongDependencyFormat, 
    valid_platforms_versions
)

#VALID_PLATFORMS = ["linux-aarch64", "linux-x86_64", "macos-x86_64", "windows-x86_64"]
#VALID_PYTHON_VERSIONS = ["3.12"]

# VALID_PLATFORMS, _ = valid_platforms_versions()
DEPENDENCY_FILE_CHANGE = datetime.strptime("Sep 17 2024","%b %d %Y").date()
MINIMUM_DATE = datetime.strptime("Apr 3 2024","%b %d %Y").date()
console = Console()

@click.command()
@click.argument('type', type=click.Choice(['integration', 'dependency']))
@click.argument('module')
@click.argument('initial', required=False)
@click.argument('final', required=False)
@click.option('--time', help="Filter commits starting from a specific date. Accepts both absolute and relative formats, "
         "such as '2025-03-01', '2 weeks ago', or 'yesterday'")
@click.option('--threshold', help="Only show modules with size differences greater than a threshold in bytes")
@click.option('--platform', help="Target platform to analyze. Only required for dependencies. If not specified, all platforms will be analyzed")
#@click.option('--python', 'version', type=click.Choice(VALID_PYTHON_VERSIONS), help="Python version (MAJOR.MINOR)")
@click.option('--compressed', is_flag=True, help="Measure compressed size")
@click.option('--csv', is_flag=True, help="Output results in CSV format")
@click.pass_obj
def timeline(app, type, module, initial, final, time, threshold, platform, compressed, csv):
    url = app.repo.path
    with GitRepo(url) as gitRepo:
        try:
            with console.status("[cyan]Fetching commits...", spinner="dots"):
                folder = module if type == 'integration' else '.deps/resolved'
                commits = gitRepo.get_module_commits(folder, initial, final, time)
                first_commit = gitRepo.get_creation_commit_module(module)
                gitRepo.checkout_commit(commits[-1])
                valid_platforms, _ = valid_platforms_versions(gitRepo.repo_dir)
                n_platforms = len(valid_platforms)
            if platform and platform not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}")
            elif commits == [''] and type == "integration" and module_exists(gitRepo.repo_dir, module):
                raise ValueError(f"No changes found: {module}")
            elif commits == [''] and type == "integration" and not module_exists(gitRepo.repo_dir, module):
                raise ValueError(f"Integration {module} not found in latest commit, is the name correct?")
            elif type == 'dependency' and platform and module not in get_dependency_list(gitRepo.repo_dir, [platform]):
                raise ValueError(f"Dependency {module} not found in latest commit for the platform {platform}, is the name correct?")
            elif type == 'dependency' and not platform and module not in get_dependency_list(gitRepo.repo_dir, valid_platforms):
                raise ValueError(f"Dependency {module} not found in latest commit, is the name correct?")
            elif type == 'dependency' and commits == ['']:
                raise ValueError(f"No changes found: {module}")
            if type == "dependency" and platform is None:
                for i, plat in enumerate(valid_platforms):
                    timeline_mode(app, gitRepo, type, module, commits, threshold, plat, compressed, csv, i, True, n_platforms, None)
            else:
                timeline_mode(app, gitRepo, type, module, commits, threshold, platform, compressed, csv, None, False, n_platforms, first_commit)
        except Exception as e:
            app.abort(str(e))


def timeline_mode(app, gitRepo, type, module, commits, threshold, platform, compressed, csv, i, maybe_mod_missing, n_platforms,first_commit):
    modules = get_repo_info(gitRepo, type, platform, module, commits, i, maybe_mod_missing,n_platforms, compressed, first_commit)
    if modules != []:
        with console.status("[cyan]Exporting data...", spinner="dots"):
            grouped_modules = group_modules(modules, platform, i)
            trimmed_modules = trim_modules(grouped_modules, threshold)
            maybe_mod_missing = False
            if csv:
                print_csv(app, i, trimmed_modules)
            else:
                print_table(app, "Timeline for " + module, trimmed_modules)

def get_repo_info(gitRepo, type, platform, module, commits, i, maybe_mod_missing, n_platforms, compressed, first_commit):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        transient=True, 
    ) as progress:
        if type == "integration":
            file_data = process_commits(commits, module, gitRepo, progress, platform, type, compressed, first_commit)
        else: 
            file_data = process_commits(commits, module, gitRepo, progress, platform, type, compressed, None)
    return file_data      
    
def process_commits(commits, module, gitRepo, progress, platform, type, compressed, first_commit=None):
    file_data=[]
    task = progress.add_task("[cyan]Processing commits...", total=len(commits))
    repo = gitRepo.repo_dir
    
    folder = module if type == 'integration' else '.deps/resolved'
    for commit in commits:
        gitRepo.sparse_checkout_commit(commit, folder)
        date, author, message = gitRepo.get_commit_metadata(commit)
        date, message, commit = format_commit_data(date, message, commit, first_commit)
        if type == 'dependency' and date < MINIMUM_DATE:
            continue
        elif type == 'dependency':
            result = get_dependencies(repo, module, platform, commit, date, author, message, compressed)
            if result:
                file_data.append(result)
        elif type == 'integration':
            file_data = get_files(repo, module, commit, date, author, message, file_data, compressed)
        progress.advance(task)
    return file_data

def get_files(repo_path, module, commit, date, author, message, file_data, compressed):   
    
    if not module_exists(repo_path, module):
        file_data.append(
                    {
                        "Size (Bytes)": 0,
                        "Date": date,
                        "Author": author,
                        "Commit Message": "(DELETED) " + message,
                        "Commit SHA": commit
                    }
                )
        return file_data    
    
    ignored_files = {"datadog_checks_dev", "datadog_checks_tests_helper"}
    # resolved_path = os.path.join(repo_path, module)

    git_ignore = get_gitignore_files(repo_path)
    included_folder = "datadog_checks/"
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Convert the path to a relative format within the repo
            relative_path = os.path.relpath(file_path, repo_path)

            # Filter files
            if is_valid_integration(relative_path, included_folder, ignored_files, git_ignore):
                size = compress(file_path) if compressed else os.path.getsize(file_path)
                file_data.append(
                    {
                        "Size (Bytes)": size,
                        "Date": date,
                        "Author": author,
                        "Commit Message": message,
                        "Commit SHA": commit
                    }
                )
    return file_data

def get_dependencies(repo_path, module, platform, commit, date, author, message, compressed):
    resolved_path = os.path.join(repo_path, ".deps/resolved")
    paths = os.listdir(resolved_path)
    version = get_version(paths, platform)
    for filename in paths:
        file_path = os.path.join(resolved_path, filename)
        if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
            download_url = get_dependency(file_path, module)
            return get_dependency_size(download_url, commit, date, author, message, compressed) if download_url else None

def get_dependency(file_path, module):
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
        for line in file_content.splitlines():
            match = re.search(r"([\w\-\d\.]+) @ (https?://[^\s#]+)", line)
            if not match:
                raise WrongDependencyFormat("The dependency format 'name @ link' is no longer supported.")
            name, url = match.groups()
            if name == module:
                return url
    return None            

def get_dependency_size(download_url, commit, date, author, message, compressed):
    if compressed:
        response = requests.head(download_url)
        response.raise_for_status()
        size = int(response.headers.get("Content-Length"))
    else:
        with requests.get(download_url, stream=True) as response:
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

    return  {
                "Size (Bytes)": size,
                "Date": date,
                "Author": author,
                "Commit Message": message,
                "Commit SHA": commit
            }

def get_version(files, platform):
    final_version = ''
    for file in files:
        if platform in file:
            version = file.split('_')[-1]
            match = re.search(r"\d+(?:\.\d+)?", version)
            version = match.group(0) if match else None
            if version > final_version:
                final_version = version
    return final_version if len(final_version) != 1 else 'py'+ final_version


def is_correct_dependency(platform, version, name):
        return platform in name and version in name



    

def group_modules(modules, platform, i):
    grouped_aux = {}

    for file in modules:
        key = (file['Date'], file['Author'], file['Commit Message'], file['Commit SHA'])
        grouped_aux[key] = grouped_aux.get(key, 0) + file["Size (Bytes)"]
    if i is None: 
        return [
            {
                "Commit SHA": commit,
                "Size (Bytes)": size,
                'Size': convert_size(size),
                'Delta (Bytes)': 'N/A',
                'Delta': 'N/A',
                "Date": date,
                "Author": author,
                "Commit Message": message,
                
            }
            for (date, author, message, commit), size in grouped_aux.items()
        ]
    else: 
        return [
            {
                "Commit SHA": commit,
                "Size (Bytes)": size,
                'Size': convert_size(size),
                'Delta (Bytes)': 'N/A',
                'Delta': 'N/A',
                "Date": date,
                "Author": author,
                "Commit Message": message,
                'Platform': platform,
            }
            for (date, author, message, commit), size in grouped_aux.items()
        ]

def trim_modules(modules, threshold=0):
    modules[0]['Delta (Bytes)'] = 0
    modules[0]['Delta'] = ' '
    trimmed_modules = [modules[0]]
    for i in range(1, len(modules)-1):
        delta = modules[i]['Size (Bytes)']-modules[i-1]['Size (Bytes)']
        if abs(delta) > int(threshold):
            modules[i]['Delta (Bytes)'] = delta
            modules[i]['Delta'] = convert_size(delta)
            trimmed_modules.append(modules[i])
    if len(modules) > 1:
        delta = modules[-1]['Size (Bytes)']-modules[-2]['Size (Bytes)']
        modules[-1]['Delta (Bytes)'] = delta
        modules[-1]['Delta'] = convert_size(delta)
        trimmed_modules.append(modules[-1])
    return trimmed_modules

def format_commit_data(date, message, commit, first_commit):
    if commit == first_commit:
        message = "(NEW) " + message
    message = message if len(message) <= 35 else message[:30].rsplit(" ", 1)[0] + "..." + message.split()[-1]
    date = datetime.strptime(date, "%b %d %Y").date()
    return date, message, commit[:7]

def module_exists(path, module):
    return os.path.exists(os.path.join(path, module))

def get_dependency_list(path, platforms):
    resolved_path = os.path.join(path, ".deps/resolved")
    all_files = os.listdir(resolved_path)
    dependencies = set()

    for platform in platforms:
        version = get_version(all_files, platform)
        for filename in all_files:
            file_path = os.path.join(resolved_path, filename)
            if os.path.isfile(file_path) and is_correct_dependency(platform, version, filename):
                with open(file_path, "r", encoding="utf-8") as file:
                    matches = re.findall(r"([\w\-\d\.]+) @ https?://[^\s#]+", file.read())
                    dependencies.update(matches)
    return dependencies
