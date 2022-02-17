ARG IBM_ACE_IMAGE

FROM ${IBM_ACE_IMAGE}

USER root

COPY compile_bars.sh /home/aceuser/compile_bars.sh
COPY bars /home/aceuser/bars
RUN  chmod -R ugo+rwx /home/aceuser

USER 1000

RUN /home/aceuser/compile_bars.sh

USER root

RUN  chmod -R ugo+rwx /home/aceuser

USER 1000
