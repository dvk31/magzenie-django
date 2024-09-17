import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_app_name(app_config):
    """
    Extracts the app name from the app configuration string.
    Example: "magazines.apps.MagazinesConfig" -> "magazines"
    """
    return app_config.split('.')[0]

def find_files(app_name):
    """
    Finds model, view, URL, and serializer files in the app directory.
    """
    app_dir = app_name
    found_files = {
        'models': [],
        'views': [],
        'urls': [],
        'serializers': []
    }
    
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if 'model' in file.lower():
                    found_files['models'].append(file_path)
                elif file == 'views.py':
                    found_files['views'].append(file_path)
                elif file == 'urls.py':
                    found_files['urls'].append(file_path)
                elif 'serializer' in file.lower():
                    found_files['serializers'].append(file_path)
    
    return found_files

def read_file(file_path):
    """
    Reads the content of a file.
    Returns the content as a string. If the file doesn't exist, returns None.
    """
    if not os.path.isfile(file_path):
        logging.warning(f"File not found: {file_path}")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    json_file = 'our_apps.json'
    output_file = 'all_code_output.txt'
    marker = '*******'

    logging.info(f"Starting to process {json_file}")

    # Check if our_apps.json exists
    if not os.path.isfile(json_file):
        logging.error(f"{json_file} not found in the current directory.")
        return

    # Read the JSON file
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing {json_file}: {e}")
        return

    apps = data.get('our_apps', [])
    if not apps:
        logging.warning("No applications found in 'our_apps'.")
        return

    logging.info(f"Found {len(apps)} apps in {json_file}")

    # Open the output file for writing
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for app_config in apps:
            app_name = extract_app_name(app_config)
            logging.info(f"Processing app: {app_name}")
            
            files = find_files(app_name)
            
            if not any(files.values()):
                logging.warning(f"No relevant files found for {app_name}")
                continue

            for file_type, file_paths in files.items():
                for file_path in file_paths:
                    logging.info(f"Processing {file_type} file: {file_path}")
                    
                    content = read_file(file_path)
                    if content is None:
                        continue  # Skip if the file doesn't exist or can't be read

                    # Write the separator and file name
                    out_f.write(f"File: {os.path.basename(file_path)} (App: {app_name}, Type: {file_type})\n")
                    out_f.write(f"{marker}\n")
                    # Write the content of the file
                    out_f.write(content)
                    out_f.write(f"\n{marker}\n\n")  # Add marker after content and extra newline for readability
                    logging.info(f"Successfully wrote {file_type} content for {app_name}")

    logging.info(f"Finished processing. Output written to {output_file}")

if __name__ == "__main__":
    main()