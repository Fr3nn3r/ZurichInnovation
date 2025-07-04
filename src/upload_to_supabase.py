import os
from supabase import create_client, Client
from dotenv import load_dotenv
import re

def get_cleaned_files(directory):
    """Gets all '-context-clean.txt' files from a directory."""
    cleaned_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith("-context-clean.txt"):
                cleaned_files.append(os.path.join(root, file))
    return cleaned_files

def extract_case_from_filename(filename):
    """Extracts the case information from the filename."""
    match = re.search(r"Case-(\d+)-context-clean.txt", os.path.basename(filename))
    if match:
        return f"Case_{match.group(1)}"
    return None

def upload_to_supabase(supabase: Client, file_path: str):
    """Uploads a single file to Supabase."""
    case_key = extract_case_from_filename(file_path)
    if not case_key:
        print(f"Could not extract case number from {file_path}. Skipping.")
        return

    context_key = f"sample_data_2_{case_key}"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        data, count = supabase.table('n8n_context_cache').insert({
            "context_key": context_key,
            "context_value": content,
            "zurich_challenge_id": "2",
            "dataset_id": "2"
        }).execute()
        print(f"Successfully uploaded {file_path} with context_key: {context_key}")
    except Exception as e:
        print(f"Error uploading {file_path}: {e}")

def main():
    """Main function to upload all cleaned files to Supabase."""
    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file.")
        return

    supabase: Client = create_client(url, key)

    output_directory = "output"
    cleaned_files = get_cleaned_files(output_directory)

    for file_path in cleaned_files:
        upload_to_supabase(supabase, file_path)

if __name__ == "__main__":
    main() 