# SQL Server Testing Guidelines

## Windows

To run the tests on Windows, an instance of MSSQL is expected to run on the host. The name of the database instance and the credentials reflect the CI environment, so that might not work out of the box on a local development environment.

## Linux

On Linux, a Docker container running a MSSQL instance is automatically started before running the tests. We use unixODBC and [FreeTDS][15] to talk to the database so, depending on the Linux distribution, you need to install additional dependencies on your local dev environment before running the tests. For example these are the installation steps for Ubuntu 14.04:

```shell
sudo apt-get install unixodbc unixodbc-dev tdsodbc
```

## OSX

Same as Linux, MSSQL runs in a Docker container and we talk to the database through unixODBC and [FreeTDS][15]. You can use [homebrew][16] to install the required packages:

```shell
brew install unixodbc freetds
```

## Failover Cluster Instance (FCI) Metrics

Failover Cluster Instance metrics will not be available using `compose` or `compose-ha` due to the special set up required.
These metrics can be found after setting up a SQL Server FCI instance following this [tutorial on GCP][17].


[15]: http://www.freetds.org
[16]: https://brew.sh
[17]: https://cloud.google.com/compute/docs/instances/sql-server/configure-failover-cluster-instance