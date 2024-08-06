import json
import os
from utilities import PATH, INTEGRATIONS, PATHS_TXT_FILE, HEURISTICS_JSON_FILE

# store all last modified date, name, and pathname in a file
def store_paths_in_text_file(top_path, dirs, file_name):
	file = open(file_name, 'w')

	for f in dirs:
		dashboards_path = f + "/assets/dashboards"
		full_dashboards_path = os.path.join(top_path, dashboards_path)
		for d in os.listdir(full_dashboards_path):
			full_path = os.path.join(full_dashboards_path, d)
			file.write(full_path + '\n')
	file.close()


def main(): 
	store_paths_in_text_file(PATH, INTEGRATIONS, PATHS_TXT_FILE)
	array = []
	f = open(PATHS_TXT_FILE, 'r')
	x = 1
	while x < 10:
		# Get next line from file
		line = f.readline()

		# if line is empty end of file is reached
		if not line:
			break
			
		integration = open(line.strip(), 'r')
		json_string = integration.read()
		json_object = json.loads(json_string)
		dict = {'path': line.split('integrations-core/')[1].strip(), 
		  		'has_ordered_layout': 'True', 
				'has_ungrouped_widgets': 'False', 
				'has_all_title_case_groups': "True" }
		for key in json_object:
			if(key == 'layout_type'):
				dict['has_ordered_layout'] = str(json_object[key] != 'free')

			# print('key: ' + key)
			if(key == 'widgets'):
				all_widgets = json_object[key]
				for widget in all_widgets:
					definition = widget["definition"]
					for def_key in definition:
						# type of widget
						if(def_key == 'type'):
							if definition[def_key] != ('group' or 'note'):
								dict['has_ungrouped_widgets'] = str(True)
							else:
								group_title = str(definition['title']).strip()
								if(len(group_title) > 1 and (not group_title.istitle())):
									dict['has_all_title_case_groups'] = str(False)

		x += 1
		array.append(dict)
	f.close()

	heuristics = open(HEURISTICS_JSON_FILE, 'w')
	heuristics.write(str(array).replace('\'', '\"'))
	heuristics.close()
  
if __name__=="__main__": 
    main() 