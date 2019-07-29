FROM jasonrivers/nagios:latest
COPY --chown=nagios:nagios nagios4/nagios.cfg /opt/nagios/etc/nagios.cfg
RUN  chown -R nagios:nagios /opt/nagios/var/
