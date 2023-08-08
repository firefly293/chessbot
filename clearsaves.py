import glob

file_pattern = "saves/*.save"

for file_path in glob.iglob(file_pattern):
    try:
        with open(file_path, 'w') as file:
            file.truncate(0)
        print(f"Emptied: {file_path}")
    except Exception as e:
        print(f"Error emptying {file_path}: {e}")