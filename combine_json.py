import os
import json
from tqdm import tqdm

def combine_json_files(directory):
    all_data = []
    
    # Iterate over all files in the directory
    for filename in tqdm(os.listdir(directory)):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            
            # Load the JSON data from the file
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
    
    # Remove duplicates by converting to a set of frozensets
    # This assumes each item in the list is a dictionary or similar hashable object
    unique_data = list({json.dumps(item, sort_keys=True) for item in all_data})

    print("LENGTH UNIQUE DATA: ", len(unique_data))
    
    # Optionally, you can write the combined and deduplicated data to a new JSON file
    with open(os.path.join(directory, 'combined_no_dup.json'), 'w') as f:
        json.dump([json.loads(item) for item in tqdm(unique_data)], f, indent=4)
    
    print(f"Combined and deduplicated data written to 'combined_deduplicated.json'.")

# Example usage
directory_path = 'Data'
combine_json_files(directory_path)
