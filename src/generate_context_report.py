import os
import json
import pandas as pd
import argparse
from tqdm import tqdm
from pathlib import Path


def extract_text_from_content(content):
    """Recursively extracts text from content which can be a string, dict, or list."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        text = ""
        for _, value in content.items():
            text += extract_text_from_content(value) + " "
        return text
    if isinstance(content, list):
        text = ""
        for item in content:
            text += extract_text_from_content(item) + " "
        return text
    return ""


def get_folder_size(path):
    """Calculates the total size of a folder in kilobytes."""
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / 1024


def estimate_tokens(text):
    """Estimates the number of tokens in a text string."""
    return len(text) / 4


def generate_context_report(
    data_dir, output_dir, excel_output_path, zurich_challenge_id
):
    """
    Generates a report from context.json files and exports it to an Excel file.
    If the Excel file exists, it updates it with new or modified entries.
    """
    context_files = list(Path(output_dir).glob("*-context.json"))
    report_data = []

    if not context_files:
        print(f"No '*-context.json' files found in {output_dir}")
        return

    print(f"Found {len(context_files)} context files to process.")

    for context_file in tqdm(context_files, desc="Processing context files"):
        basefoldername = context_file.name.replace("-context.json", "")

        # Search for the original folder within the data directory
        original_folder_path = next(Path(data_dir).rglob(basefoldername), None)

        folder_size_kb = 0
        if original_folder_path and original_folder_path.is_dir():
            folder_size_kb = get_folder_size(original_folder_path)
        else:
            print(
                f"Warning: Original folder not found for {basefoldername} in {data_dir}"
            )

        full_text_content = ""
        try:
            with open(context_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                full_text_content = extract_text_from_content(json_data)
        except Exception as e:
            print(f"Warning: Could not process file {context_file}: {e}")
            continue

        estimated_tokens_count = estimate_tokens(full_text_content)

        report_data.append(
            {
                "basefoldername": basefoldername,
                "folder_size_in_KB": folder_size_kb,
                "estimated_tokens": estimated_tokens_count,
                "zurich_challenge_id": zurich_challenge_id,
            }
        )

    if not report_data:
        print("No data was generated for the report.")
        return

    new_df = pd.DataFrame(report_data)

    if Path(excel_output_path).exists():
        try:
            existing_df = pd.read_excel(excel_output_path)
            # Use 'basefoldername' as key for merging/updating
            # Remove old entries for the same basefoldername and append new ones
            existing_df = existing_df[
                ~existing_df["basefoldername"].isin(new_df["basefoldername"])
            ]
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            df = combined_df
            print(f"Updating existing report at: {excel_output_path}")
        except Exception as e:
            print(
                f"Could not read existing excel file {excel_output_path}. It will be overwritten. Error: {e}"
            )
            df = new_df
    else:
        df = new_df

    # Ensure output directory exists
    Path(excel_output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(excel_output_path, index=False)

    print(f"Report successfully generated/updated at: {excel_output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a report from context JSON files."
    )
    parser.add_argument(
        "--data_dir", type=str, default="data", help="Path to the data directory."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="output",
        help="Path to the output directory containing context files.",
    )
    parser.add_argument(
        "--excel_output_path",
        type=str,
        default="output/context_report.xlsx",
        help="Path to save the output Excel report.",
    )
    parser.add_argument(
        "--zurich_challenge_id",
        type=str,
        required=True,
        help='Zurich Challenge ID (e.g., "02- Claims- Motor Liability- UK").',
    )

    args = parser.parse_args()

    generate_context_report(
        args.data_dir, args.output_dir, args.excel_output_path, args.zurich_challenge_id
    )
