# As the NVML integration is a community integration, it is not packaged with the Agent image by default. A custom image with the packaged integration should therefore be used in containerized environments.
# Setup taken from https://docs.datadoghq.com/agent/guide/use-community-integrations/?tab=docker

# Installs the NVML integration version 1.0.6.
# See the changelog for the other versions that are available (https://github.com/DataDog/integrations-extras/blob/master/nvml/CHANGELOG.md)
FROM gcr.io/datadoghq/agent:latest
RUN agent integration install -t -r datadog-nvml==1.0.6

# Use the permalink to the requirements to install the PIP libraries used by the check
RUN curl https://raw.githubusercontent.com/DataDog/integrations-extras/c94cd62f61bcd763ae18a601f0862da308563c03/nvml/requirements.in > requirements.in && /opt/datadog-agent/embedded/bin/pip3 install -r requirements.in

# Why do you need these variables: See https://github.com/NVIDIA/nvidia-docker/wiki/Usage
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES all