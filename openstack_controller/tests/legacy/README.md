# Openstack Controller Integration E2E

The Openstack_controller integration includes three E2E environments:

## py27
Available out-of-the-box:
    
` ddev env start openstack_controller py27` 

## py38
Available out-of-the-box:
    
` ddev env start openstack_controller py38` 

## py38-sandbox
Requires a running Google Cloud Openstack VM instance running  

To use the `py38-sandbox` environment, the following environment variables must be configured:

**Environment Variables**

* TF_VAR_google_credentials_file: Local file path containing Service Account Credentials
* TF_VAR_google_compute_instance_name: Name of the VM Instance [here](https://console.cloud.google.com/compute/instances?project=datadog-integrations-lab) 

**Start the E2E Environment**

`ddev env start openstack_controller py38-sandbox`