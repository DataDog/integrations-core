ARG NAGIOS_VERSION
FROM jasonrivers/nagios:${NAGIOS_VERSION}
COPY --chown=nagios:nagios nagios4/nagios.cfg /opt/nagios/etc/nagios.cfg
RUN  chown -R nagios:nagios /opt/nagios/var/
