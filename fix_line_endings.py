import os
from pathlib import Path


def convert_line_endings(directory):
    extensions_to_convert = ['.py', '.ipynb', '.toml', '.lock']
    print("Starting line-ending-fixer-upper...")
    for root, dirs, files in os.walk(directory):
        if '.git' in dirs:
            dirs.remove('.git') # Skip the .git folder
        if ".venv" in dirs:
            dirs.remove(".venv")
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext in extensions_to_convert:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                        lines = file.readlines()
                    with open(filepath, 'w', newline='\n', encoding='utf-8') as file:
                        file.writelines(lines)
                    print("Fixed line endings for: ", filepath)
                except UnicodeDecodeError:
                    print(f"Error decoding file: {filepath}")

if __name__ == "__main__":
    directory = str(Path(__file__).parent)
    extensions_to_convert = ['.py', '.ipynb', '.toml', '.lock']
    convert_line_endings(directory)
