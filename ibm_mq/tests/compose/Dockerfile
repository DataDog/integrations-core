# pull from custom ibm_mqv8 image
FROM datadog/docker-library:ibm_mq_v8

WORKDIR /

RUN echo '* Enable Queue Monitoring \n\
ALTER QMGR MONQ(MEDIUM)' >> /etc/mqm/config.mqsc