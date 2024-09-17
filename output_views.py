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

def find_views_file(app_name):
    """
    Finds the views.py file in the specified app directory.
    """
    app_dir = app_name
    views_file = os.path.join(app_dir, 'views.py')
    if os.path.isfile(views_file):
        return views_file
    return None

def read_views_file(file_path):
    """
    Reads the content of a views file.
    Returns the content as a string. If the file doesn't exist, returns None.
    """
    if not os.path.isfile(file_path):
        logging.warning(f"Views file not found: {file_path}")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    json_file = 'our_apps.json'
    output_file = 'codeoutput.txt'
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
            
            views_file = find_views_file(app_name)
            
            if not views_file:
                logging.warning(f"No views.py file found for {app_name}")
                continue

            logging.info(f"Processing views file: {views_file}")
            
            views_content = read_views_file(views_file)
            if views_content is None:
                continue  # Skip if the views file doesn't exist or can't be read

            # Write the separator and file name
            out_f.write(f"File: {os.path.basename(views_file)} (App: {app_name})\n")
            out_f.write(f"{marker}\n")
            # Write the content of the views file
            out_f.write(views_content)
            out_f.write(f"\n{marker}\n\n")  # Add marker after content and extra newline for readability
            logging.info(f"Successfully wrote views content for {app_name}")

    logging.info(f"Finished processing. Output written to {output_file}")

if __name__ == "__main__":
    main()