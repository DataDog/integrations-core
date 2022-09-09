-- 
-- Boost Settings
-- 

REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_poller_mem_limit', '1024');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_redirect', 'on');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_enable', 'on');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_interval', '60');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_max_records', '1000000');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_max_records_per_select', '50000');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_max_runtime', '1200');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_string_length', '2000');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_string_length', '2000');
REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_rrd_update_system_enable', 'on');

-- Boost PNG cache settings
-- REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_png_cache_enable', '');
-- REPLACE INTO `%DB_NAME%`.`settings` (`name`, `value`) VALUES('boost_png_cache_directory', '/cacti/cache/boost/');