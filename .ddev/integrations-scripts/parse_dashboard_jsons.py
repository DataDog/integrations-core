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

def evaluate_widgets(widgets):
	dict = {'query_values': {
			'total': 0,
			'have_timeseries_background': 0,
			'have_conditional_formats': 0,
		 }}
	if(len(widgets) < 1):
		return
	for w in widgets:
		definition = w['definition']

		# checking on query values
		if(definition['type'] == 'query_value'):
			dict['query_values']['total'] += 1

			# uses timeseries background
			if('timeseries_background' in definition):
				dict['query_values']['have_timeseries_background'] += 1

			# has conditional formatting
			if('requests' in definition and 'conditional_formats' in definition['requests'][0] and len(definition['requests'][0]['conditional_formats']) > 0):
				dict['query_values']['have_conditional_formats'] += 1	
	return dict


def main(): 
	store_paths_in_text_file(PATH, INTEGRATIONS, PATHS_TXT_FILE)
	array = []
	f = open(PATHS_TXT_FILE, 'r')
	x = 1
	while x < 20:
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
				'has_all_title_case_groups': "True",
				'has_overview_section': 'False',
				'about_section': {
					'contains_about_text': 'False',
					'contains_banner_img': 'False'
				},
				'widgets': {
					'query_values': {
						'total': 0,
						'have_timeseries_background': 0,
						'have_conditional_formats': 0
					}
				}}

		is_first = True
		for key in json_object:
			if(key == 'layout_type'):
				dict['has_ordered_layout'] = str(json_object[key] != 'free')

			if(key == 'widgets'):
				all_widgets = json_object[key]
				for widget in all_widgets:
					definition = widget["definition"]
					for def_key in definition:
						# group or note widget at top level
						if(def_key == 'type'):
							if(definition[def_key] != ('group' or 'note')):
								dict['has_ungrouped_widgets'] = str(True)
							
							if(definition[def_key] == 'group'):
								# has title case groups
								group_title = str(definition['title']).strip()
								if(len(group_title) > 1 and (not group_title.istitle())):
									dict['has_all_title_case_groups'] = str(False)

								# overview group
								has_overview_section = group_title.lower().find('overview')
								if(has_overview_section > 0):
									dict['has_overview_section'] = str(True)


								# first group
								if(is_first):
									contains_about_text = group_title.lower().find('about')
									if(contains_about_text > 0):
										dict['about_section']['contains_about_text'] = str(True)
									contains_banner_img = 'banner_img' in definition and definition['banner_img'] != None
									if(contains_banner_img):
										dict['about_section']['contains_banner_img'] = str(True)

									is_first = False


								# iterate through widgets
								if('widgets' in definition):
									evaluated = evaluate_widgets(definition['widgets'])
									dict['widgets']['query_values']['total'] += evaluated['query_values']['total']
									dict['widgets']['query_values']['have_timeseries_background'] += evaluated['query_values']['have_timeseries_background']
									dict['widgets']['query_values']['have_conditional_formats'] += evaluated['query_values']['have_conditional_formats']
									

		x += 1
		array.append(dict)
	f.close()

	heuristics = open(HEURISTICS_JSON_FILE, 'w')
	heuristics.write(str(array).replace('\'', '\"'))
	heuristics.close()
  
if __name__=="__main__": 
    main() 