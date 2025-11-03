# Nutanix Integration Installation

Follow these steps to install and configure the Nutanix integration.

## Installation

1.  **Download the wheel package**
    Download the latest release of the Nutanix integration wheel package.

2.  **Install the wheel**
    Use the following command to install the wheel package. Replace `<PATH_TO_WHL>` with the actual path to the downloaded `.whl` file.

    ```bash
    sudo -u dd-agent datadog-agent integration install -w <PATH_TO_WHL>
    ```

## Configuration

1.  **Create a configuration file**
    Create a configuration file for the Nutanix integration at `/etc/datadog-agent/conf.d/nutanix.d/conf.yaml`. You can use the auto-generated `conf.yaml.example` file in the same directory as a template.

2.  **Edit the configuration file**
    Fill in the required parameters in your `conf.yaml`:

    ```yaml
    instances:
      - pc_ip: <YOUR_PRISM_CENTRAL_IP>
        pc_username: <YOUR_PRISM_CENTRAL_USERNAME>
        pc_password: <YOUR_PRISM_CENTRAL_PASSWORD>
        tls_verify: <true_or_false>
    ```

    - `pc_ip`: The IP address of your Prism Central instance.
    - `pc_username`: The username for your Prism Central instance.
    - `pc_password`: The password for your Prism Central instance.
    - `tls_verify`: Set to `true` to enable TLS verification, or `false` to disable it.

3.  **Required Permissions**
    The user configured in `conf.yaml` must have the following permissions in Prism Central:

    - Cluster Viewer
    - Virtual Machine Viewer

4.  **Restart the Agent**
    Restart the Datadog Agent to apply the new configuration.
