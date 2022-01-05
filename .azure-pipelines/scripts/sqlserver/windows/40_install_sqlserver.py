import subprocess

from tenacity import wait_exponential, retry, stop_after_attempt


@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(5))
def install_msoledbsql():
    print("Install Microsoft OLE DB Driver for SQL Server ...")
    subprocess.run(["choco", "install", "msoledbsql", "--no-progress", "-y"], check=True)


install_msoledbsql()
