import random
import sys
import time


def main():
    if len(sys.argv) < 2:
        sys.exit(0)
    
    metrics_file = sys.argv[1]

    while True:
        read_and_get_new_metrics(metrics_file)
        sleep_time = random.randint(1, 30)
        time.sleep(sleep_time)


def read_and_get_new_metrics(metrics_file):
    with open(metrics_file, "r+") as metrics:
        new_content = []
        for line in metrics.readlines():
            line = line.rstrip('\n')
            if line == "":
                new_content.append(line)
                continue
            if line.startswith("#"): 
                new_content.append(line)
                continue

            fields = line.split(" ")

            metric_name = fields[0]
            value_str = fields[-1]

            is_percentage = "percentage" in metric_name

            value = None
            is_float = False

            if "." in value_str:
                is_float = True
                value = float(value_str)
            else:
                value = int(value_str)
            
            new_value = modify_value(value, is_percentage, is_float)
            new_line = fields[:-1]
            new_line.append(str(new_value))
            new_content.append(" ".join(new_line))
            
        new_file_content = "\n".join(new_content)
        metrics.seek(0)
        metrics.write(new_file_content)

def modify_value(value, is_percentage, is_float):
    if is_float and value == 0.0:
        value = random.uniform(0.0, 0.2)
    if not is_float and value == 0:
        value = random.randint(0, 20)
    change_percent = random.uniform(0.05, 0.15)
    change_direction = random.choice([1, -1])
    change = value * (change_percent * change_direction)
    new_value = value + change

    if is_percentage:
        new_value = min(new_value, 1.0)
        new_value = max(new_value, 0.0)
    
    if not is_float:
        return int(new_value)
    return new_value

if __name__ == "__main__":
    main()
