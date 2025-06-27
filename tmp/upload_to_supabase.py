import os
import csv
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Increase the CSV field size limit to 10MB
csv.field_size_limit(10 * 1024 * 1024)

# Load environment variables from .env file
load_dotenv()

# Supabase project details from the environment variables
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Check if the environment variables are set
if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in the .env file.")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(url, key)


def upload_csv_to_supabase(file_path):
    """
    Reads a CSV file and upserts its data into the 'n8n_context_cache' table in Supabase,
    ensuring that 'dataset_id' is unique.

    Args:
        file_path (str): The path to the CSV file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dataset_id = row.get("dataset_id")

                if not dataset_id:
                    print(f"Skipping row due to missing dataset_id in {file_path}")
                    continue

                # Prepare data for upsert
                data_to_upsert = {
                    "zurich_challenge_id": row.get("zurich_challenge_id"),
                    "dataset_id": dataset_id,
                    "context_value": row.get("context_value"),
                    "context_key": dataset_id,  # Using dataset_id as the unique context_key
                }

                # Perform the upsert operation
                response = (
                    supabase.table("n8n_context_cache")
                    .upsert(data_to_upsert, on_conflict="dataset_id")
                    .execute()
                )

                print(f"Upserted row for dataset_id: {dataset_id}")

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}")


if __name__ == "__main__":
    file_to_upload = "canada_output.csv"

    if not os.path.exists(file_to_upload):
        print(f"Error: The file '{file_to_upload}' was not found.")
    else:
        print(f"--- Starting upload for {file_to_upload} ---")
        upload_csv_to_supabase(file_to_upload)
        print(f"--- Finished upload for {file_to_upload} ---")
