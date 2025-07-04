import os
import sys
import subprocess

# List of required packages
required_packages = ["supabase", "python-dotenv", "tqdm"]


def install_packages():
    """Install required Python packages."""
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


# Install packages before proceeding
install_packages()

from supabase import create_client, Client
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env file, overriding any existing vars to ensure updates take effect
load_dotenv(override=True)

# Supabase project details from the environment variables
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

# Check if the environment variables are set
if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in the .env file.")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(url, key)


def upload_context_files_to_supabase(directory: str):
    """
    Reads all files ending in '-context-clean.txt' from a directory and upserts their data
    into the 'n8n_context_cache' table in Supabase.

    Args:
        directory (str): The path to the directory containing the context files.
    """
    print(f"Scanning directory: {directory}")

    try:
        files_to_process = [
            f for f in os.listdir(directory) if f.endswith("-context-clean.txt")
        ]
        if not files_to_process:
            print("No files ending with '-context-clean.txt' found in the directory.")
            return

        with tqdm(
            total=len(files_to_process), desc="Uploading context files", unit="file"
        ) as pbar:
            for filename in files_to_process:
                file_path = os.path.join(directory, filename)

                # Extract dataset_id from filename, e.g., "Case-123" from "Case-123-context-clean.txt"
                dataset_id = filename.replace("-context-clean.txt", "")

                pbar.set_postfix_str(f"Processing: {filename}")

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Prepare data for upsert
                    data_to_upsert = {
                        "dataset_id": dataset_id,
                        "context_value": content,
                        "context_key": "sample_data_2",  # Set to the required constant value
                        "zurich_challenge_id": "05- Claims- Liability Decisions- Canada",  # Set to the required constant value
                    }

                    # Perform the upsert operation
                    response = (
                        supabase.table("n8n_context_cache")
                        .upsert(data_to_upsert, on_conflict="dataset_id")
                        .execute()
                    )

                    # Check for errors in the response
                    if hasattr(response, "error") and response.error:
                        tqdm.write(
                            f"  -> Failed to upsert row for dataset_id: {dataset_id}. Error: {response.error.message}"
                        )
                    else:
                        # Optionally, you can write a success message, but the progress bar shows progress.
                        # tqdm.write(f"  -> Successfully upserted row for dataset_id: {dataset_id}")
                        pass

                except FileNotFoundError:
                    tqdm.write(
                        f"  -> Error: The file '{file_path}' was not found during processing."
                    )
                except Exception as e:
                    tqdm.write(
                        f"  -> An error occurred while processing {file_path}: {e}"
                    )

                pbar.update(1)

    except FileNotFoundError:
        print(f"Error: The directory '{directory}' was not found.")
    except Exception as e:
        print(f"An error occurred while scanning the directory: {e}")


if __name__ == "__main__":
    output_directory = "output"
    print("--- Starting upload of context files to Supabase ---")
    upload_context_files_to_supabase(output_directory)
    print("--- Finished upload process ---")
