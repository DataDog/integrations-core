import os
import shutil
import tempfile
import subprocess

class GitRepo:
    def __init__(self, url):
        self.url = url
        self.repo_dir = None

    def __enter__(self):
        self.repo_dir = tempfile.mkdtemp()
        self._run("git init")
        self._run(f"git remote add origin {self.url}")
        return self

    def _run(self, cmd):
        subprocess.run(cmd, shell=True, cwd=self.repo_dir, check=True)

    def checkout_commit(self, commit):
        self._run(f"git fetch --depth 1 origin {commit}")
        self._run(f"git checkout {commit}")


    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)