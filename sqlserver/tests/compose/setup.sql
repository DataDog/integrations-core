-- Backup master
BACKUP DATABASE master TO DISK = N'/test' WITH FORMAT,
  MEDIANAME = 'master',
  MEDIADESCRIPTION = 'Backup master';

-- AdventureWorks databases
--
RESTORE DATABASE [AdventureWorks2017] FROM  DISK = N'/var/opt/mssql/backup/AdventureWorks2017.bak' WITH
FILE = 1,  MOVE N'AdventureWorks2017' TO N'/var/opt/mssql/data/AdventureWorks2017.mdf',
MOVE N'AdventureWorks2017_log' TO N'/var/opt/mssql/data/AdventureWorks2017_log.ldf',
REPLACE, NOUNLOAD,  STATS = 2;
