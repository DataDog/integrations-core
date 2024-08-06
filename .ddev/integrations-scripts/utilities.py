import os
from datetime import datetime, date

ONE_YEAR = 365
PATH = os.path.dirname(os.path.dirname(os.getcwd())) # ../../ this is the integrations-core top level directory
RESULTS_TXT_FILE = "results.txt"
RESULTS_JSON_FILE = "results.json"
STATS_TXT_FILE = "stats.txt"
PATHS_TXT_FILE = "paths.txt"
HEURISTICS_JSON_FILE = "heuristics.json"

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

# ex. ['twistlock', 'dcgm', 'cloudera', 'btrfs', 'activemq', 'nvidia_jetson', 'temporal',....]
INTEGRATIONS = get_dashboard_directories(PATH)