FROM kong:0.13.0

# get ContainerPilot release
ENV CONTAINERPILOT_VERSION 2.7.2
RUN apk update && apk add curl
RUN export CP_SHA1=e886899467ced6d7c76027d58c7f7554c2fb2bcc \
    && curl -SLso /tmp/containerpilot.tar.gz \
         "https://github.com/joyent/containerpilot/releases/download/${CONTAINERPILOT_VERSION}/containerpilot-${CONTAINERPILOT_VERSION}.tar.gz"
RUN export CP_SHA1=e886899467ced6d7c76027d58c7f7554c2fb2bcc \
    && echo "${CP_SHA1}  /tmp/containerpilot.tar.gz" | sha1sum -c

RUN tar zxf /tmp/containerpilot.tar.gz -C /bin \
    && rm /tmp/containerpilot.tar.gz

# add ContainerPilot configuration
COPY containerpilot.json /etc/containerpilot.json
ENV CONTAINERPILOT=file:///etc/containerpilot.json

CMD /bin/containerpilot kong start

EXPOSE 8000 8443 8001 7946
