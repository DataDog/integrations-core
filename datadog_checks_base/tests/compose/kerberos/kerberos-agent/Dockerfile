FROM datadog/agent:7.25.0-rc.4

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y -qq && apt-get install -y --no-install-recommends \
  less \
  vim

COPY configurenginx.sh /opt/install/configurenginx.sh
COPY configurekerberos.sh /opt/install/configurekerberos.sh
COPY entrypoint.sh /opt/install/entrypoint.sh

RUN chmod +x /opt/install/configurenginx.sh \
    && chmod +x /opt/install/configurekerberos.sh \
    && chmod +x /opt/install/entrypoint.sh

ENTRYPOINT ["/opt/install/entrypoint.sh"]
