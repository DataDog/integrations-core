FROM sath89/oracle-12c

COPY instant-client-basic.zip instant-client-sdk.zip /
RUN mkdir /instant-client
RUN apt-get update && apt-get install -y unzip

ENTRYPOINT unzip /instant-client-\*.zip -d /instant-client && mv /instant-client/*/* /instant-client/ && /entrypoint.sh
