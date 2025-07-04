import glob
import subprocess
import sys

# Find all JSON files in the output directory
json_files = glob.glob("output/*_evaluation.json")

if not json_files:
    print("No evaluation JSON files found in the 'output' directory.")
    sys.exit(1)

# Construct the command to run the export script
command = [sys.executable, "src/export_to_excel.py"] + json_files

try:
    print("Generating combined Excel report...")
    subprocess.run(command, check=True)
    print("--- Report generation complete. ---")
except subprocess.CalledProcessError as e:
    print("Failed to generate the Excel report.")
    print(f"Return code: {e.returncode}")
    print(f"Output: {e.output}")
except FileNotFoundError:
    print("Error: 'src/export_to_excel.py' not found.")
