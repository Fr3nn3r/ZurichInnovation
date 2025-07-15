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
