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
