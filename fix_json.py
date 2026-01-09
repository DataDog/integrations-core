import ast
import json
import re

file_path = 'prefect/tests/fixtures/post_metrics.json'

with open(file_path, 'r') as f:
    content = f.read()

split_marker = '"/events/filter": {'
parts = content.split(split_marker)

if len(parts) != 2:
    print("Could not find split marker.")
    exit(1)

part1 = parts[0]
part2 = parts[1]

start_idx = part2.find('[')
end_idx = part2.rfind(']')
list_str = part2[start_idx : end_idx + 1]

# Revert JSON literals to Python literals for ast parsing
# We assume the file currently has 'null', 'true', 'false' from previous failed attempts
# or 'None', 'True', 'False' from original state.
# We normalize to Python literals.
list_str_fixed = re.sub(r':\s*null', ': None', list_str)
list_str_fixed = re.sub(r':\s*true', ': True', list_str_fixed)
list_str_fixed = re.sub(r':\s*false', ': False', list_str_fixed)

# Fix missing commas
list_str_fixed = re.sub(r"}\s*{'event'", "}, {'event'", list_str_fixed)

try:
    events_list = ast.literal_eval(list_str_fixed)
    json_str = json.dumps(events_list, indent=2)
    new_part2 = part2[:start_idx] + json_str + part2[end_idx + 1 :]
    new_content = part1 + split_marker + new_part2

    with open(file_path, 'w') as f:
        f.write(new_content)
    print("File updated successfully.")

except Exception as e:
    print(f"Error: {e}")
    lines = list_str_fixed.splitlines()
    if hasattr(e, 'lineno'):
        print(f"Line {e.lineno}: {lines[e.lineno - 1]}")
    exit(1)
