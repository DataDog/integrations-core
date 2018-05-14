FROM sath89/oracle-12c

COPY ./oracle_jdbc.jar /oracle_jdbc.jar
RUN mkdir /driver

ENTRYPOINT cp /oracle_jdbc.jar /driver && /entrypoint.sh

