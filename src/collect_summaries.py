# This script is responsible for organizing and centralizing meeting summaries.
# It scans a root 'data' directory for files named 'Meeting Recording_summary.txt',
# which are assumed to be located in subdirectories with a specific naming
# convention (e.g., '01- Claims- Travel- Canada').
#
# The script performs the following steps:
# 1. Finds all summary files within the 'data' directory.
# 2. For each summary, it identifies the numbered parent folder to extract a
#    unique identifier and a descriptive name.
# 3. It sanitizes the folder name to create a clean, URL-friendly string.
# 4. It checks for the presence of 'Follow-Up' in the names of any .mp4 files
#    in the same directory to determine if the summary is for a follow-up meeting.
# 5. Based on this information, it constructs a new, standardized filename in the
#    format 'AMA-XX-folder-name.txt' or 'AMA-XX-folder-name-follow-up.txt'.
# 6. Finally, it copies and renames the summary files to a centralized
#    'AMA-summaries' directory.
#
# A progress bar is displayed to track the copying process.
#
# Usage:
#   python src/collect_summaries.py

import re
import shutil
from pathlib import Path
from tqdm import tqdm


def sanitize_name(name: str) -> str:
    """Sanitizes the folder name part for the new filename."""
    # Remove leading/trailing whitespace and replace spaces with hyphens
    sanitized = name.strip().replace(" ", "-")
    # Remove any characters that are not alphanumeric or hyphen
    sanitized = re.sub(r"[^a-zA-Z0-9-]", "", sanitized)
    # Replace multiple hyphens with a single one
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized


def main():
    """
    Collects all summaries, renames them, and copies them to AMA-summaries folder.
    """
    data_root = Path("data")
    output_root = Path("AMA-summaries")
    output_root.mkdir(exist_ok=True)

    print(f"Scanning for summaries in '{data_root}'...")
    summary_files = list(data_root.rglob("Meeting Recording_summary.txt"))

    if not summary_files:
        print("No summary files found.")
        return

    print(f"Found {len(summary_files)} summary files. Copying and renaming...")

    copied_count = 0
    with tqdm(total=len(summary_files), desc="Copying summaries", unit="file") as pbar:
        for summary_path in summary_files:
            # Find the numbered parent folder (e.g., '01- Claims- Travel- Canada')
            numbered_folder = None
            for part in summary_path.parts:
                if re.match(r"^\d+-", part):
                    numbered_folder = part
                    break

            if not numbered_folder:
                print(
                    f"⚠️ Could not find numbered parent for: {summary_path}. Skipping."
                )
                continue

            # Extract number and name from folder
            match = re.match(r"^(\d+)-\s*(.*)", numbered_folder)
            if not match:
                print(f"⚠️ Could not parse folder name: {numbered_folder}. Skipping.")
                continue

            folder_num = int(match.group(1))
            folder_name = match.group(2)

            sanitized_folder_name = sanitize_name(folder_name)

            # Check for 'Follow-Up' in video names within the same directory
            is_follow_up = False
            video_files = list(summary_path.parent.glob("*.mp4"))
            if any("Follow-Up" in v.name for v in video_files):
                is_follow_up = True

            # Construct the new filename
            if is_follow_up:
                new_filename = (
                    f"AMA-{folder_num:02d}-{sanitized_folder_name}-follow-up.txt"
                )
            else:
                new_filename = f"AMA-{folder_num:02d}-{sanitized_folder_name}.txt"

            dest_path = output_root / new_filename

            shutil.copy(summary_path, dest_path)
            copied_count += 1
            pbar.update(1)

    print(f"\n✅ Done. Copied {copied_count} files to '{output_root}'.")


if __name__ == "__main__":
    main()
