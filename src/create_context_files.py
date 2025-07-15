# This script is a data aggregation tool designed to create consolidated "context"
# files from various source files related to insurance claims. It operates on a
# specific, predefined directory structure, targeting subfolders within 'Fault' and
# 'Split liability' directories inside a main 'Sample 2 Claims files OCR' folder.
#
# The script's main functionalities are:
# 1.  **Dependency Management**: It includes a simple function to ensure that the
#     `tqdm` package, used for progress bars, is installed before the main logic
#     runs.
#
# 2.  **Targeted File Aggregation**: For each individual claim folder, the script
#     scans for and reads content from two main sources:
#     - **Text-Based Files**: It recursively searches for common text formats
#       (`.md`, `.html`, `.json`, `.txt`) and appends their entire content to the
#       context file.
#     - **Image Damage Analyses**: It identifies image files (`.jpg`, `.png`, etc.)
#       within the claim folder and then looks for a corresponding
#       '-damage-analysis.txt' file in the 'output' directory. If found, the
#       content of this analysis file is also included in the context.
#
# 3.  **Context File Generation**: The aggregated text from all these sources is
#     then written into a single, consolidated text file named after the claim
#     folder (e.g., 'claim_folder_name-context.txt'). These context files are
#     all saved in a centralized 'output' directory.
#
# 4.  **Structured Output**: The content from each source file is clearly delineated
#     within the context file using headers (e.g., '--- Content from [filename] ---'),
#     making it easy to trace the origin of each piece of information.
#
# 5.  **Progress Tracking**: It uses the `tqdm` library to display a progress bar,
#     providing a visual indication of how many claim folders have been processed.
#
# Usage:
#   python src/create_context_files.py
#
#   Note: The input directory is hardcoded to 'Sample 2 Claims files OCR' and the
#   output directory is hardcoded to 'output'.

import os
import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """
    Checks if all necessary dependencies are installed and, if not, installs them.
    """
    try:
        import tqdm
    except ImportError:
        print("Installing required dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
        print("Dependencies installed successfully.")


def create_context_for_directory(directory_path: Path, output_dir: Path):
    """
    Creates a context file for a single directory.
    """
    all_text = []

    # Find and read all text-based files
    for extension in [".md", ".html", ".json", ".txt"]:
        for file_path in directory_path.rglob(f"*{extension}"):
            # Exclude the output files themselves to avoid recursion
            if "context.txt" in file_path.name:
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    all_text.append(f"--- Content from {file_path.name} ---\n")
                    all_text.append(f.read())
                    all_text.append("\n\n")
            except Exception as e:
                print(f"Could not read file {file_path}: {e}")

    # Find and read damage analysis files from the output folder
    for image_file in directory_path.rglob("*"):
        if image_file.is_file() and image_file.suffix.lower() in [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
        ]:
            base_filename = image_file.stem
            analysis_file_name = f"{base_filename}-damage-analysis.txt"
            analysis_file_path = output_dir / analysis_file_name

            if analysis_file_path.exists():
                try:
                    with open(analysis_file_path, "r", encoding="utf-8") as f:
                        all_text.append(
                            f"--- Image Analysis from {analysis_file_path.name} ---\n"
                        )
                        all_text.append(f.read())
                        all_text.append("\n\n")
                except Exception as e:
                    print(f"Could not read analysis file {analysis_file_path}: {e}")

    if not all_text:
        return  # Don't create empty files

    # Create output file
    context_file_name = f"{directory_path.name}-context.txt"
    output_file_path = output_dir / context_file_name

    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write("".join(all_text))
    print(f"Created context file: {output_file_path}")


def main():
    install_dependencies()
    from tqdm import tqdm

    # The main directory containing 'Fault' and 'Split liability'
    base_dir = Path("Sample 2 Claims files OCR")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Directories to process
    sub_dirs_to_process = [base_dir / "Fault", base_dir / "Split liability"]

    claim_folders = []
    for sub_dir in sub_dirs_to_process:
        if sub_dir.is_dir():
            for item in sub_dir.iterdir():
                if item.is_dir():
                    claim_folders.append(item)

    if not claim_folders:
        print("No claim folders found to process.")
        return

    for directory in tqdm(claim_folders, desc="Processing claim folders"):
        create_context_for_directory(directory, output_dir)


if __name__ == "__main__":
    main()
