import subprocess

from tenacity import wait_exponential, retry, stop_after_attempt


@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(5))
def install_sqlserver():
    """
    Install SQL Server locally for testing the native client.
    See https://docs.microsoft.com/en-us/sql/relational-databases/native-client/sql-server-native-client
    """
    print("Install sql-server-2017 ...")
    subprocess.run(["choco", "install", "sql-server-2017", "--no-progress"], check=True)


@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(5))
def install_msoledbsql():
    print("Install Microsoft OLE DB Driver for SQL Server ...")
    subprocess.run(["choco", "install", "msoledbsql", "--no-progress", "-y"], check=True)


install_msoledbsql()
install_sqlserver()
