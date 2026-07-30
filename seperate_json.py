import json
import os

# Input JSON file containing the array of steps
INPUT_JSON = "data.json"

# Folder where individual JSON files will be stored
OUTPUT_DIR = "data"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Read the JSON file
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# Ensure the input is a list
if not isinstance(data, list):
    raise ValueError("Input JSON must contain a list of step objects.")

# Save each step as a separate JSON file
for step in data:

    step_id = step.get("step_id")

    if not step_id:
        print("Skipping object without step_id")
        continue

    output_file = os.path.join(OUTPUT_DIR, f"{step_id}.json")

    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(step, out, indent=4)

    print(f"Saved: {output_file}")

print(f"\nDone! {len(data)} files created in '{OUTPUT_DIR}'")