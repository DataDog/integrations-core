# Running Istio E2E Test Environment

## Overview

This test config uses Terraform[1] to setup and initialize a Kubernetes cluster
on Google Cloud Platform.  Once some user config is in place, it works just
like other `ddev env` operations, but there are some different dependencies.

## Terraform Version

Ensure that you have Terraform installed, and are running at least version
`0.12`,  and as of the time of this writing, the stable version was `0.12.16`.
If you have an older version installed, you can check and update using the
`tfenv` command.

## Initialization

Running `ddev env start istio` from scratch will likely result in a core dump
from terraform.  Navigate to `istio/tests/terraform` and execute
`terraform validate`.  This should output a series of plugin requirements
errors, now you can initialize via `terraform init` and see the output text
`Terraform has been successfully initialized!`.

## GCP Account File

In order to correctly deploy, create an environment variable pointing to your
GCP yaml credentials, like so:

    $ export TF_VAR_account_json=<path_to_json_file>

## Starting env

With the env initialized, you starting up the env as usual will work:

    $ ddev env start istio py37


It will take some time for the pods to get deployed and initialized on GCP,
expect around 10 minutes.


[1]: https://www.terraform.io
