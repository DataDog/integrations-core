FROM jboss/wildfly:latest

RUN /opt/jboss/wildfly/bin/add-user.sh datadog dog --silent

CMD ["/opt/jboss/wildfly/bin/standalone.sh", "-b", "0.0.0.0", "-bmanagement", "0.0.0.0"]
