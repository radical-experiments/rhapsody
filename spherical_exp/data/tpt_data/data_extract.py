import re
from pathlib import Path
import os
import json

def extract_total_tokens(text):
    pattern = r"Total tokens/second for service (\d+):\s*([\d\.]+)"
    matches = re.findall(pattern, text)

    #print(matches)

    # Convert matches to dict: {service_id: value}
    results = [float(val) for _, val in matches]

    print(sum(results) , len(results))

    return sum(results) / 10   #len(results)


# Example: read from a log file
# with open("logfile.txt", "r") as f:
#     log_text = f.read()

log_text = """
... paste your log text here ...
"""

directory  = Path('tpt_data')

all_data = {}

for filename in os.listdir(directory):
    file_path = os.path.join(directory, filename)

    print(filename)

    exp_name = filename.split('_')[0]

    # Skip subdirectories
    if not os.path.isfile(file_path):
        continue

    # Read file text
    with open(file_path, "r") as f:
        text = f.read()

    #print(f"\n--- Reading file: {filename} ---")
    #print(text[:200])  # print first 200 chars (optional)

    # Process text here...

    print(filename)
    values = extract_total_tokens(text)
    print(values)

    d = {}

    all_data.setdefault(exp_name, []).extend([values])


with open("tpt.json", "w") as f:
    json.dump(all_data, f, indent=2)
