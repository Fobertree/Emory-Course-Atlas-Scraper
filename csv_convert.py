import json
import csv

# Load JSON data
with open('coursedata.json') as f:
    data = json.load(f)

# Extract field names for CSV header
fieldnames = data[0].keys() if data else []

# Write CSV file
with open('output.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)