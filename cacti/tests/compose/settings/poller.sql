--
-- Poller settings
--

-- How often to poll data in seconds
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('poller_interval', '60');

-- How often the cronjob is set to run
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('cron_interval', '300');

-- The maximum threads allowed per process. Using a higher number when using Spine will improve performance. Required settings are 10-15. Values above 50 are most often insane and may degrade preformance
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('max_threads', '1');

-- Number of instances to run
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('concurrent_processes', '1');