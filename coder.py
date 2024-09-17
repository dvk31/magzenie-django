

import os
import re
import sys

def parse_code_file(code_file_path):
    """
    Parses the code.py file and extracts file paths with their corresponding code blocks.
    
    Returns:
        A list of tuples: [(file_path, code), ...]
    """
    with open(code_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex pattern to capture sections like ### a. `path/to/file.py` followed by ```python code ```
    pattern = re.compile(
        r'###\s+[a-z]\.\s+`([^`]+)`\s*```python\s*([\s\S]*?)```',
        re.MULTILINE
    )

    matches = pattern.findall(content)
    file_code_list = []

    for match in matches:
        file_path = match[0].strip()
        code = match[1].rstrip()
        file_code_list.append((file_path, code))
    
    return file_code_list

def create_or_overwrite_file(file_path, code):
    """
    Creates directories and files as needed. Overwrites the file if it already exists.
    
    Args:
        file_path (str): Relative path to the file.
        code (str): Code content to write into the file.
    """
    # Normalize the file path
    file_path = os.path.normpath(file_path)
    
    # Get directory and file name
    directory, filename = os.path.split(file_path)
    
    # Create directories if they don't exist
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Full path
    full_path = os.path.join(os.getcwd(), file_path)
    
    # Write (overwrite) the code to the file
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"Wrote to file: {full_path}")

def main():
    # Define the path to code.py
    code_file = 'code.py'
    
    if not os.path.isfile(code_file):
        print(f"Error: '{code_file}' does not exist in the current directory.")
        sys.exit(1)
    
    # Parse the code file
    file_code_pairs = parse_code_file(code_file)
    
    if not file_code_pairs:
        print("No file paths and code blocks found in 'code.py'.")
        sys.exit(1)
    
    # Process each file and its code
    for file_path, code in file_code_pairs:
        create_or_overwrite_file(file_path, code)
    
    print("All files have been processed successfully.")

if __name__ == "__main__":
    main()
