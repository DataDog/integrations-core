# Teradata Integration E2E

The Teradata integration includes two E2E environments:

## py38
Available out-of-the-box:
    
` ddev env start teradata py38` 

## py38-sandbox
Requires a running Teradata instance configured with a Datadog user (see the [Teradata Datadog documentation](https://github.com/DataDog/integrations-core/blob/master/teradata/README.md) installation instructions). The instance may be running locally or cloud-hosted. 

To use the `py38-sandbox` environment, the following environment variables must be configured:

**Environment Variables**

* TERADATA_SERVER: hostname or IP address pointing to the server on which the Teradata database is running
* TERADATA_DD_USER: Teradata Datadog username
* TERADATA_DD_PW: Teradata Datadog password 

**Start the E2E Environment**

`ddev env start teradata py38-sandbox`