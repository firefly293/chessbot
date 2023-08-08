import glob

file_pattern = "saves/*.save"

for file_path in glob.iglob(file_pattern):
    try:
        with open(file_path, 'w') as file:
            file.truncate(0)
        print(f"emptied {file_path}")
    except Exception as e:
        print(f"error emptying {file_path}: {e}")