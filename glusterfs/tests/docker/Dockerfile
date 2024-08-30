# Start from the base image
FROM gluster/gluster-centos:latest

RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo && \
    sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo && \
    sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo

# Install Python 3
RUN yum install -y python3 && yum clean all

# Download the gstatus binary
RUN curl -LO https://github.com/gluster/gstatus/releases/download/v1.0.5/gstatus \
    && chmod +x ./gstatus \
    && mv ./gstatus /usr/local/bin/gstatus

# Start the glusterd service with the specified options
# CMD ["/usr/sbin/glusterd", "-p", "/var/run/glusterd.pid", "--log-level", "INFO"]