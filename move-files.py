import os
import shutil

# Set up paths
downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
cpp_file = "BlueprintBuilder.cpp"
h_file = "BlueprintBuilder.h"

cpp_dest_folder = r"C:\Junk\BlueprintLLMTest\Plugins\BlueprintLLM\Source\BlueprintLLM\Private"
h_dest_folder = r"C:\Junk\BlueprintLLMTest\Plugins\BlueprintLLM\Source\BlueprintLLM\Public"

# Function to move file to destination, replacing any existing file
def move_file(source_path, dest_folder):
    if os.path.exists(source_path):
        dest_path = os.path.join(dest_folder, os.path.basename(source_path))
        
        # If the destination file exists, remove it
        if os.path.exists(dest_path):
            os.remove(dest_path)
        
        # Move the file to the destination
        shutil.move(source_path, dest_path)
        print(f"Moved {source_path} to {dest_path}")
    else:
        print(f"Source file {source_path} does not exist!")

# Paths to the source files
cpp_source_path = os.path.join(downloads_folder, cpp_file)
h_source_path = os.path.join(downloads_folder, h_file)

# Move the files
move_file(cpp_source_path, cpp_dest_folder)
move_file(h_source_path, h_dest_folder)