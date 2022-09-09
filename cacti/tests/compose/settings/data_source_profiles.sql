--
-- Enable 1 minute polling data source profile
--

REPLACE INTO `%DB_NAME%`.`data_source_profiles` (`id`,`hash`,`name`,`step`,`heartbeat`,`x_files_factor`,`default`) VALUES('4', 'bba8b254a188680cf53a7f6a75721e29','1 Minute Polling','60','120','0.5','on');

REPLACE INTO `%DB_NAME%`.`data_source_profiles_cf` (`data_source_profile_id`,`consolidation_function_id`) VALUES('4','1');
REPLACE INTO `%DB_NAME%`.`data_source_profiles_cf` (`data_source_profile_id`,`consolidation_function_id`) VALUES('4','2');
REPLACE INTO `%DB_NAME%`.`data_source_profiles_cf` (`data_source_profile_id`,`consolidation_function_id`) VALUES('4','3');
REPLACE INTO `%DB_NAME%`.`data_source_profiles_cf` (`data_source_profile_id`,`consolidation_function_id`) VALUES('4','4');

REPLACE INTO `%DB_NAME%`.`data_source_profiles_rra` (`id`, `data_source_profile_id`,`name`,`steps`,`rows`) VALUES('10','4','Daily','1','1440');
REPLACE INTO `%DB_NAME%`.`data_source_profiles_rra` (`id`, `data_source_profile_id`,`name`,`steps`,`rows`) VALUES('11','4','Weekly','1','10080');
REPLACE INTO `%DB_NAME%`.`data_source_profiles_rra` (`id`, `data_source_profile_id`,`name`,`steps`,`rows`) VALUES('12','4','Monthly (5 minute avg)','5','8760');
REPLACE INTO `%DB_NAME%`.`data_source_profiles_rra` (`id`, `data_source_profile_id`,`name`,`steps`,`rows`) VALUES('13','4','Yearly (1 hour avg)','60','8760');

REPLACE INTO `%DB_NAME%`.`data_source_profiles` (`id`,`hash`,`name`,`step`,`heartbeat`,`x_files_factor`,`default`) VALUES('1','d62c52891f4f9688729a5bc9fad91b18','System Default','300','600','0.5','');