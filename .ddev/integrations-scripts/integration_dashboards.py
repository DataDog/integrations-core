import os
from datetime import datetime, date
from utilities import ONE_YEAR, PATH, INTEGRATIONS, RESULTS_TXT_FILE, RESULTS_JSON_FILE, STATS_TXT_FILE

# all directories that include an 'assets/dashboards' directory
def get_dashboard_directories(top_path):
	arr = []
	for f in os.listdir(top_path):
		dirPath = os.path.join(top_path, f)
		if os.path.isdir(dirPath):
			for a in os.listdir(dirPath):
				if(a == "assets"):
					assetsPath = os.path.join(dirPath, a)
					for d in os.listdir(assetsPath):
						if d == "dashboards":
							arr.append(f)
	return arr

def is_dashboard_outdated(modified_date, days_outdated):
	date_split = modified_date.split('-')
	difference_in_days = datetime.now() - datetime(int(date_split[0]), int(date_split[1]), int(date_split[2]))
	if(difference_in_days.days > (days_outdated)):
		return True
	return False

# store all last modified date, name, and pathname in a file
def store_bash_calls_in_text_file(top_path, dirs, file_name):
	for f in dirs:
		dashboards_path = f + "/assets/dashboards"
		full_dashboards_path = os.path.join(top_path, dashboards_path)
		for d in os.listdir(full_dashboards_path):
			full_path = os.path.join(full_dashboards_path, d)
			
			logAdd = 'git log -n 1 --pretty=format:\"%cd%ae&%an\" --date=format:"%Y-%m-%d&" ' + full_path + ' >> ./' + file_name
			os.system(logAdd)

			path_for_json = os.path.join(dashboards_path, d)
			os.system('echo \"&' + path_for_json + '\">> ./' + file_name)



def get_sorted_dict_by_modified_date(results_file):
	file = open(results_file, 'r')

	# iterate through files and store in an object
	dict = []

	while True:
		# Get next line from file
		line = file.readline()

		# if line is empty end of file is reached
		if not line:
			break

		attrs = line.split('&')
		dict.append({'last_modified': attrs[0], 'email': attrs[1], 'name': attrs[2], 'path': attrs[3].strip()})

	# python mutates array in place
	dict.sort(
		key=lambda x: datetime.strptime(x['last_modified'], '%Y-%m-%d')
	)
	file.close()
	return dict

def store_sorted_dict_in_json_file(dict, file_name):
	jsonFile = open(file_name, 'w')
	jsonFile.write(str(dict).replace('\'', '\"'))
	jsonFile.close()

def get_dashboard_stats(results_file):
	total_integration_dashboards = 0
	integration_dashboards_outdated_2_years = 0
	integration_dashboards_outdated_1_year = 0
	file = open(results_file, 'r')

	while True:
		# Get next line from file
		line = file.readline()

		# if line is empty end of file is reached
		if not line:
			break

		attrs = line.split('&')
		total_integration_dashboards += 1

		if(is_dashboard_outdated(attrs[0], ONE_YEAR)):
			integration_dashboards_outdated_1_year += 1

		if(is_dashboard_outdated(attrs[0], ONE_YEAR * 2)):
			integration_dashboards_outdated_2_years += 1

	file.close()
	return [total_integration_dashboards, integration_dashboards_outdated_2_years, integration_dashboards_outdated_1_year]


def store_dashboard_stats_in_text_file(stats, file_name):
	file = open(file_name, 'w')
	file.write('Results as of ' + str(date.today()) + '\n')
	if(stats[0] > 0):
		percent_outdated_1_year = (stats[2] / stats[0]) * 100
		percent_outdated_2_years = (stats[1] / stats[0]) * 100
		# include actual numbers
		file.write('Total 1 year: ' + str(stats[2]) + '\n')
		file.write('Total 2 years: ' + str(stats[1]) + '\n')
		file.write('Total: ' + str(stats[0]) + '\n')
		file.write('Dashboards outdated 1 year: ' + str(percent_outdated_1_year) + '%\n')
		file.write('Dashboards outdated 2 years: ' + str(percent_outdated_2_years) + '%')
	file.close()

def main(): 
	store_bash_calls_in_text_file(PATH, INTEGRATIONS, RESULTS_TXT_FILE)
	dict = get_sorted_dict_by_modified_date(RESULTS_TXT_FILE)
	store_sorted_dict_in_json_file(dict, RESULTS_JSON_FILE)
	stats = get_dashboard_stats(RESULTS_TXT_FILE)
	store_dashboard_stats_in_text_file(stats, STATS_TXT_FILE) 
  
if __name__=="__main__": 
    main() 