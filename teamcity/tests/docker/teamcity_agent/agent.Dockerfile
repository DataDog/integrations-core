FROM jetbrains/teamcity-agent

COPY test_sample.py /test_sample.py

USER root

# Update and install pip
RUN curl -s https://package.perforce.com/perforce.pubkey | gpg --dearmor | tee /usr/share/keyrings/perforce.gpg && \
    echo 'deb [signed-by=/usr/share/keyrings/perforce.gpg] https://package.perforce.com/apt/ubuntu focal release' > /etc/apt/sources.list.d/perforce.list && \
    apt-get update && \
    apt-get -y --no-install-recommends install python3-pip