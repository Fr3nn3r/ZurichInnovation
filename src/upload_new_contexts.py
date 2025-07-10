import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client


def install_dependencies():
    """
    Checks if all necessary dependencies are installed and, if not, installs them.
    """
    try:
        import tqdm
        import supabase
        import dotenv
    except ImportError:
        print("Installing required dependencies...")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "supabase",
                "python-dotenv",
                "tqdm",
            ]
        )
        print("Dependencies installed successfully.")


def main():
    install_dependencies()
    from tqdm import tqdm

    load_dotenv(override=True)

    # --- Supabase Connection ---
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not all([url, key]):
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in the .env file.")
        sys.exit(1)

    try:
        supabase: Client = create_client(url, key)
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        sys.exit(1)

    # --- File Processing ---
    output_dir = Path("output")
    context_files = list(output_dir.glob("*-context.txt"))

    if not context_files:
        print("No context files found in the 'output' directory.")
        return

    print(f"Found {len(context_files)} context files to upload.")

    # --- Data Upload ---
    table_name = "n8n_context_cache"
    zurich_challenge_id = "02- Claims- Motor Liability- UK"
    data_upload_id = "zurich_07_2025"

    for file_path in tqdm(context_files, desc="Uploading Context Files"):
        base_filename = file_path.name.replace("-context.txt", "")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                context_value = f.read().replace("\u0000", "")

            data_to_upload = {
                "context_key": base_filename,
                "dataset_id": base_filename,
                "context_value": context_value,
                "zurich_challenge_id": zurich_challenge_id,
                "data_upload_id": data_upload_id,
            }

            # Check if a row with the same context_key already exists
            select_response = (
                supabase.table(table_name)
                .select("id")
                .eq("context_key", base_filename)
                .execute()
            )

            if select_response.data:
                # Update the existing row
                tqdm.write(f"Updating existing record for {base_filename}...")
                response = (
                    supabase.table(table_name)
                    .update(data_to_upload)
                    .eq("context_key", base_filename)
                    .execute()
                )
            else:
                # Insert a new row
                tqdm.write(f"Inserting new record for {base_filename}...")
                response = supabase.table(table_name).insert(data_to_upload).execute()

            # The API response for insert/update is in response.data
            if len(response.data) == 0:
                tqdm.write(
                    f"Warning: No data returned for {base_filename}. Response: {response}"
                )

        except Exception as e:
            tqdm.write(f"An error occurred while processing {file_path.name}: {e}")

    print("\n--- Upload process complete. ---")


if __name__ == "__main__":
    main()
