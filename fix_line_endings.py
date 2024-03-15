import os

def convert_line_endings(directory):
    extensions_to_convert = ['.py', '.ipynb', '.toml', '.lock']

    for root, dirs, files in os.walk(directory):
        if '.git' in dirs:
            dirs.remove('.git')  # Skip the .git folder
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext in extensions_to_convert:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                        lines = file.readlines()
                    with open(filepath, 'w', newline='\n', encoding='utf-8') as file:
                        file.writelines(lines)
                except UnicodeDecodeError:
                    print(f"Error decoding file: {filepath}")

directory = 'C:\\Users\\kokrishnan\\code\\jupyrest2'
gitignore_file = "C:\\Users\\kokrishnan\\code\\jupyrest2\\.gitignore"
convert_line_endings(directory)
