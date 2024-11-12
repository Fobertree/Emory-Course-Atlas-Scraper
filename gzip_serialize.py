import json
import gzip

with open('Data/combined_no_dup.json') as f:
    json_data = json.load(f)

with gzip.open("Data/combined_no_dup.json.gz", "wt", encoding="utf-8") as f:
    f.write(str(json_data))

'''
Decompress:
with gzip.open("data.json.gz", "rt", encoding="utf-8") as f:
    decompressed_data = json.load(f)
'''