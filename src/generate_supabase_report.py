import os
import sys
import csv
import logging
from pathlib import Path
import tiktoken
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# --- Supabase Configuration ---
load_dotenv(override=True)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


def get_supabase_client() -> Client:
    """Initializes and returns the Supabase client."""
    logging.info(f"Supabase URL: {'Loaded' if SUPABASE_URL else 'Not Found'}")
    logging.info(f"Supabase Key: {'Loaded' if SUPABASE_KEY else 'Not Found'}")
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.error("Supabase URL or Key not found. Make sure a .env file exists.")
        sys.exit(1)
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Supabase client initialized successfully.")
        return client
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
        sys.exit(1)


def estimate_tokens(content: str) -> int:
    """Estimates the number of tokens in a string."""
    if not content:
        return 0
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(content))
    except Exception as e:
        logging.error(f"Could not estimate tokens: {e}")
        return 0


def fetch_and_generate_report(output_path: Path):
    """
    Fetches records from Supabase, estimates tokens, and generates a CSV report.
    """
    supabase = get_supabase_client()

    logging.info("Fetching all records from 'n8n_context_cache'...")
    try:
        response = supabase.table("n8n_context_cache").select("*").execute()
    except Exception as e:
        logging.error(f"Failed to fetch data from Supabase: {e}")
        return

    if not response.data:
        logging.warning("No data found in 'n8n_context_cache' table.")
        return

    records = response.data
    logging.info(f"Successfully fetched {len(records)} records.")

    if not records:
        return

    # Prepare for CSV writing
    # Dynamically get headers from the first record, excluding 'context_value'
    first_record = {k: v for k, v in records[0].items() if k != "context_value"}
    headers = list(first_record.keys()) + ["context_value_tokens"]

    # Ensure dataset_id and context_value_tokens are ordered nicely if they exist
    if "dataset_id" in headers:
        headers.pop(headers.index("context_value_tokens"))
        headers.insert(headers.index("dataset_id") + 1, "context_value_tokens")

    logging.info(f"Saving CSV report to {output_path}...")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            for record in records:
                token_count = estimate_tokens(record.get("context_value", ""))
                report_record = {
                    k: v for k, v in record.items() if k != "context_value"
                }
                report_record["context_value_tokens"] = token_count
                writer.writerow(report_record)
        logging.info(f"Successfully created CSV report at {output_path}")
    except Exception as e:
        logging.error(f"Failed to save CSV report: {e}")


if __name__ == "__main__":
    try:
        output_dir = Path("output")
        report_file = output_dir / "supabase_context_report.csv"
        fetch_and_generate_report(report_file)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
