import os
import sys
import json
import logging
import argparse
from pathlib import Path
import pandas as pd
import tiktoken

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# --- Helper Functions ---


def get_folder_size_kb(folder_path: Path) -> float:
    """Calculates the total size of a folder and its contents in kilobytes."""
    total_size_bytes = 0
    if not folder_path.is_dir():
        logging.warning(f"Folder not found: {folder_path}. Size will be reported as 0.")
        return 0.0

    for entry in folder_path.rglob("*"):
        if entry.is_file():
            total_size_bytes += entry.stat().st_size

    return total_size_bytes / 1024


def estimate_tokens(file_path: Path) -> int:
    """Estimates the number of tokens in a JSON context file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Serialize the JSON content to a string to count tokens
        content_str = json.dumps(data)

        # Use tiktoken for estimation, cl100k_base is common for gpt-4o
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(content_str))
        return num_tokens
    except Exception as e:
        logging.error(f"Could not estimate tokens for {file_path}: {e}")
        return 0


# --- Main Logic ---


def analyze_and_report(
    output_folder: str, data_root_folder: str, excel_output_path: str
):
    """
    Analyzes context files to estimate tokens and calculate folder sizes,
    then appends the results to an Excel sheet.
    """
    output_path = Path(output_folder)
    data_root_path = Path(data_root_folder)
    excel_file = Path(excel_output_path)

    # If the provided path is a directory, create a default filename inside it
    if excel_file.is_dir():
        logging.info(
            f"Provided Excel path is a directory. Defaulting to 'analysis_report.xlsx' inside it."
        )
        excel_file = excel_file / "analysis_report.xlsx"

    if not output_path.is_dir():
        logging.error(f"Output folder not found: {output_path}")
        return

    if not data_root_path.is_dir():
        logging.error(f"Data root folder not found: {data_root_path}")
        return

    logging.info(f"Scanning for context files in: {output_path}")
    context_files = list(output_path.glob("*-context.json"))

    if not context_files:
        logging.warning("No '*-context.json' files found to analyze.")
        return

    # Prepare DataFrame for Excel
    columns = ["basefoldername", "folder_size_in_KB", "estimated_tokens"]
    if excel_file.exists():
        logging.info(f"Appending to existing Excel file: {excel_file}")
        df = pd.read_excel(excel_file)
    else:
        logging.info(f"Creating new Excel file: {excel_file}")
        df = pd.DataFrame(columns=columns)

    new_rows = []
    for context_file in context_files:
        logging.info(f"Processing file: {context_file.name}")

        # Extract basefolder name from filename
        basefoldername = context_file.name.replace("-context.json", "")

        # Calculate original folder size
        original_folder_path = data_root_path / basefoldername
        folder_size_kb = get_folder_size_kb(original_folder_path)

        # Estimate tokens in the context file
        tokens = estimate_tokens(context_file)

        new_rows.append(
            {
                "basefoldername": basefoldername,
                "folder_size_in_KB": folder_size_kb,
                "estimated_tokens": tokens,
            }
        )
        logging.info(
            f"  - Basefolder: {basefoldername}, Size: {folder_size_kb:.2f} KB, Tokens: {tokens}"
        )

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        # Use concat instead of append
        df = pd.concat([df, new_df], ignore_index=True)
        # Drop duplicates based on the basefoldername to avoid re-adding data
        df.drop_duplicates(subset=["basefoldername"], keep="last", inplace=True)

        try:
            df.to_excel(excel_file, index=False)
            logging.info(f"Successfully updated Excel file: {excel_file}")
        except Exception as e:
            logging.error(f"Failed to write to Excel file {excel_file}: {e}")


# --- CLI Interface ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze context files and append results to an Excel sheet."
    )
    parser.add_argument(
        "output_folder",
        type=str,
        help="The folder containing the '*-context.json' files to analyze.",
    )
    parser.add_argument(
        "data_root_folder",
        type=str,
        help="The root directory where the original data folders are stored.",
    )
    parser.add_argument(
        "excel_output_path",
        type=str,
        help="The path to the output Excel file to create or update.",
    )

    args = parser.parse_args()

    analyze_and_report(
        args.output_folder, args.data_root_folder, args.excel_output_path
    )
