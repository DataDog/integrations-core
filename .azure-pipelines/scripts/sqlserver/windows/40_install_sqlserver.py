import subprocess

from tenacity import wait_exponential, retry, stop_after_attempt


@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(5))
def install_sqlserver():
    """
    Install with TCP/IP enabled, see: https://chocolatey.org/packages/sql-server-2017
    """
    print("Install sql-server-2017 ...")
    subprocess.run(["choco", "install", "sql-server-2017", "--no-progress", "--params", "'/TCPENABLED:1'"], check=True)


install_sqlserver()
