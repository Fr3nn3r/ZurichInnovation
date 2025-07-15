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


def upload_context_files(output_folder: str):
    """
    Scans for '*-context.json' files, reads their content, and upserts them
    to the 'n8n_context_cache' table in Supabase.
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
                "zurich_challenge_id": "01- Claims- Travel- Canada",
                "data_upload_id": "zurich_07_2025",
            }

            # --- Check-Then-Act Logic ---
            # 1. Check if a record with the same dataset_id exists
            select_response = (
                supabase_client.table("n8n_context_cache")
                .select("id")
                .eq("dataset_id", dataset_id)
                .execute()
            )

            if select_response.data:
                # 2. If it exists, update it
                logging.info(
                    f"  -> Found existing record for dataset_id: {dataset_id}. Updating..."
                )
                update_response = (
                    supabase_client.table("n8n_context_cache")
                    .update(data_to_upsert)
                    .eq("dataset_id", dataset_id)
                    .execute()
                )
                if hasattr(update_response, "error") and update_response.error:
                    logging.error(
                        f"  -> Failed to update {context_key}: {update_response.error.message}"
                    )
                else:
                    logging.info(f"  -> Successfully updated: {context_key}")
            else:
                # 3. If it does not exist, insert it
                logging.info(
                    f"  -> No record found for dataset_id: {dataset_id}. Inserting..."
                )
                insert_response = (
                    supabase_client.table("n8n_context_cache")
                    .insert(data_to_upsert)
                    .execute()
                )
                if hasattr(insert_response, "error") and insert_response.error:
                    logging.error(
                        f"  -> Failed to insert {context_key}: {insert_response.error.message}"
                    )
                else:
                    logging.info(f"  -> Successfully inserted: {context_key}")

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

    upload_context_files(args.output_folder)
