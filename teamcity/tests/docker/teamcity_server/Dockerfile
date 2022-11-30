FROM jetbrains/teamcity-server:2022.10

COPY TeamCity_Backup.zip /TeamCity_Backup.zip

RUN /opt/teamcity/bin/maintainDB.sh restore -A /data/teamcity_server/datadir -I -F /TeamCity_Backup.zip