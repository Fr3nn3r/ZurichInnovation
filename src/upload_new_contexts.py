# This script is designed to upload context data, stored in local JSON files, to a
# Supabase table named 'n8n_context_cache'. It scans a specified folder for files
# matching the pattern '*-context.json', reads their content, and then inserts
# this data into the database.
#
# The script's main functionalities are:
# 1.  **Supabase Integration**: It securely connects to a Supabase project using
#     credentials (URL and Key) stored in environment variables, which are loaded
#     from a `.env` file.
#
# 2.  **File Scanning**: It scans a target directory (typically the 'output' folder)
#     for JSON files that end with '-context.json'. These files are expected to
#     be generated by other scripts in the workflow, like `generate_context.py`.
#
# 3.  **Data Preparation**: For each file found, it extracts a `dataset_id` from the
#     filename and prepares a data payload for Supabase. This payload includes the
#     file content, the dataset ID, and some hardcoded metadata like
#     `zurich_challenge_id` and `data_upload_id`.
#
# 4.  **Upsert Logic**: For each context file, the script will perform an "upsert"
#     operation into the 'n8n_context_cache' table. It checks for a record with
#     the same `dataset_id` and `zurich_challenge_id`; if one exists, it updates
#     it. Otherwise, it inserts a new record. This prevents duplicate entries for
#     the same dataset.
#
# 5.  **Logging and Error Handling**: The script provides clear logging for each step
#     of the process, including which file is being processed and the success or
#     failure of each database operation. It also handles potential exceptions
#     during file processing and database interaction.
#
# 6.  **Command-Line Interface**: It includes a simple command-line interface to
#     specify the target folder containing the context files and an optional flag
#     for verbose logging output.
#
# Usage:
#   - To upload files from the default 'output' folder:
#     `python src/upload_new_contexts.py`
#   - To specify a different folder:
#     `python src/upload_new_contexts.py /path/to/your/output_folder`

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,  # Default level
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# --- Supabase Configuration ---
load_dotenv(override=True)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


def get_supabase_client():
    """Initializes and returns the Supabase client if credentials are available."""
    if SUPABASE_URL and SUPABASE_KEY:
        logging.info("Supabase client initialized.")
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.warning("Supabase URL or Key not found. Cannot proceed.")
    return None


# --- Main Logic ---


def upload_context_files(
    output_folder: str, zurich_challenge_id: str, data_upload_id: str
):
    """
    Scans for '*-context.json' files, reads their content, and upserts them
    into the 'n8n_context_cache' table in Supabase.
    """
    supabase_client = get_supabase_client()
    if not supabase_client:
        return

    output_path = Path(output_folder)
    if not output_path.is_dir():
        logging.error(f"Output folder not found: {output_path}")
        return

    logging.info(f"Scanning for context files in: {output_path}")
    context_files = list(output_path.glob("*-context.json"))

    if not context_files:
        logging.warning("No '*-context.json' files found to upload.")
        return

    logging.info(f"Found {len(context_files)} context files to process.")

    for context_file in context_files:
        dataset_id = context_file.name.replace("-context.json", "")
        context_key = context_file.name
        logging.info(f"Processing {context_file.name}...")

        try:
            with open(context_file, "r", encoding="utf-8") as f:
                context_value = f.read()

            data_to_upsert = {
                "context_key": context_key,
                "dataset_id": dataset_id,
                "context_value": context_value,
                "zurich_challenge_id": zurich_challenge_id,
                "data_upload_id": data_upload_id,
            }

            # --- Upsert Logic ---
            # The script will update the record if a context with the same
            # dataset_id and zurich_challenge_id already exists. Otherwise, it
            # will insert a new record.
            logging.info(f"  -> Upserting record for dataset_id: {dataset_id}...")
            upsert_response = (
                supabase_client.table("n8n_context_cache")
                .upsert(
                    data_to_upsert,
                    on_conflict="dataset_id,zurich_challenge_id",
                )
                .execute()
            )

            if hasattr(upsert_response, "error") and upsert_response.error:
                logging.error(
                    f"  -> Failed to upsert {context_key}: {upsert_response.error.message}"
                )
            else:
                logging.info(f"  -> Successfully upserted: {context_key}")

        except Exception as e:
            logging.error(
                f"An exception occurred during processing of {context_key}: {e}"
            )


# --- CLI Interface ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload context files to Supabase.")
    parser.add_argument(
        "output_folder",
        type=str,
        default="output",
        nargs="?",  # Makes the argument optional
        help="The folder containing the '*-context.json' files. Defaults to 'output'.",
    )
    parser.add_argument(
        "--zurich-challenge-id",
        type=str,
        required=True,
        help="The Zurich Challenge ID.",
    )
    parser.add_argument(
        "--data-upload-id",
        type=str,
        required=True,
        help="The data upload ID.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging output.",
    )

    args = parser.parse_args()

    # Configure logging level based on verbosity flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    upload_context_files(
        args.output_folder, args.zurich_challenge_id, args.data_upload_id
    )
