FROM jetbrains/teamcity-agent

COPY test_sample.py /test_sample.py

USER root

# Update and install pip
RUN apt-get update && \
    apt-get -y --no-install-recommends install python3-pip