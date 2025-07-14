import os
import sys
import json
import logging
import argparse
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import pandas as pd

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# --- Import from existing scripts ---
# It's better to refactor these scripts into importable functions,
# but for now, we'll try to import them directly.
try:
    from simple_ocr import process_pdf_ocr_only, pytesseract
    from image_to_text_analyzer import OPENAI_API_KEY
    from PIL import Image
    from openai import OpenAI
except (ImportError, ModuleNotFoundError) as e:
    logging.error(f"Failed to import necessary modules: {e}")
    logging.error(
        "Please ensure that the required packages are installed and that the script is run from the project root."
    )
    sys.exit(1)

# --- Constants ---
SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".json",
    ".md",
    ".xml",
    ".html",
    ".csv",
    ".py",
    ".js",
}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
SUPPORTED_SHEET_EXTENSIONS = {".csv", ".xls", ".xlsx"}

# --- File Processing Functions ---


def get_file_type(file_path: Path) -> str:
    """Detects the file type based on extension."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    if ext in SUPPORTED_SHEET_EXTENSIONS:
        return "sheet"
    if (
        ext in SUPPORTED_TEXT_EXTENSIONS or file_path.stat().st_size < 1000000
    ):  # Guess for text files
        # Check mime type for text
        mimetype, _ = mimetypes.guess_type(file_path)
        if mimetype and mimetype.startswith("text/"):
            return "text"
    return "unsupported"


def read_text_file(file_path: Path) -> Optional[str]:
    """Reads content from a text-based file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Could not read text file {file_path}: {e}")
        return None


def read_sheet_file(file_path: Path) -> Optional[str]:
    """Reads content from a CSV or Excel file and converts to JSON."""
    try:
        if file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        return df.to_json(orient="records")
    except Exception as e:
        logging.error(f"Could not read sheet file {file_path}: {e}")
        return None


def get_image_ocr_text(file_path: Path) -> str:
    """Extracts text from an image using Tesseract OCR."""
    try:
        return pytesseract.image_to_string(Image.open(file_path))
    except Exception as e:
        logging.error(f"OCR failed for image {file_path}: {e}")
        return ""


def get_image_ai_description(client: OpenAI, file_path: Path) -> str:
    """Generates a description for an image using OpenAI."""
    try:
        with open(file_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

        # Using a more generic prompt than the one in image_to_text_analyzer.py
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe the contents of this image.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI analysis failed for {file_path}: {e}")
        return ""


# --- Main Orchestration Function ---


def generate_context(basefolder: str, output_folder: Optional[str] = None) -> None:
    """
    Recursively scans a base folder, extracts content from files, and
    generates a JSON context file.
    """
    basefolder = basefolder.strip("'\"")  # Clean up path from shell quoting issues
    base_path = Path(basefolder)
    if not base_path.is_dir():
        logging.error(
            f"Error: The base folder '{basefolder}' does not exist or is not a directory."
        )
        return

    output_path = Path(output_folder) if output_folder else Path.cwd()
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / f"{base_path.name}-context.json"
    logging.info(f"Output will be saved to: {output_file}")

    # Initialize OpenAI client if the key is available
    client = None
    if OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
    else:
        logging.warning(
            "OPENAI_API_KEY not found. AI descriptions for images will be skipped."
        )

    all_files_context: List[Dict[str, Any]] = []

    # Use rglob for recursive scanning
    files_to_process = list(base_path.rglob("*"))
    logging.info(f"Found {len(files_to_process)} files to process in {base_path}.")

    for file_path in files_to_process:
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(base_path).as_posix()
        logging.info(f"Processing: {relative_path}")

        file_type = get_file_type(file_path)
        content: Union[str, Dict[str, str], None] = None

        entry = {
            "relative_path": relative_path,
            "file_type": file_type,
            "content": None,
        }

        try:
            if file_type == "pdf":
                content = process_pdf_ocr_only(str(file_path))
            elif file_type == "image":
                ai_description = ""
                if client:
                    ai_description = get_image_ai_description(client, file_path)
                else:
                    logging.warning(
                        f"Skipping AI description for {relative_path} due to missing API key."
                    )

                ocr_text = get_image_ocr_text(file_path)
                content = {"ai_description": ai_description, "ocr_text": ocr_text}
            elif file_type == "text":
                content = read_text_file(file_path)
            elif file_type == "sheet":
                content = read_sheet_file(file_path)
            else:
                logging.warning(
                    f"Unsupported file type for {relative_path}. Skipping content extraction."
                )
                all_files_context.append(entry)
                continue

            if content is not None:
                entry["content"] = content
                all_files_context.append(entry)
            else:
                logging.warning(
                    f"Skipping {relative_path} due to content extraction failure."
                )

        except Exception as e:
            logging.error(
                f"An unexpected error occurred processing {relative_path}: {e}"
            )
            # Add entry with no content if processing fails
            all_files_context.append(entry)

    # Write the final JSON output
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_files_context, f, indent=2, ensure_ascii=False)
        logging.info(f"Successfully generated context file at {output_file}")
    except Exception as e:
        logging.error(f"Failed to write JSON output to {output_file}: {e}")


# --- CLI Interface ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a context JSON file from a directory of files."
    )
    parser.add_argument(
        "basefolder",
        type=str,
        help="The base folder to recursively scan for files.",
    )
    parser.add_argument(
        "--output_folder",
        type=str,
        default=None,
        help="The folder to save the output JSON file. Defaults to the current working directory.",
    )

    args = parser.parse_args()

    # Tesseract path configuration check
    # The original script has a hardcoded path. We should check if it's set.
    if not pytesseract.pytesseract.tesseract_cmd:
        logging.warning("Tesseract command path is not set in pytesseract.")
        logging.warning(
            "Please ensure Tesseract is in your system's PATH or set the path in the script."
        )
    else:
        # Check if the configured path exists
        tesseract_path = pytesseract.pytesseract.tesseract_cmd.strip('"')
        if not os.path.exists(tesseract_path):
            logging.error(f"Tesseract executable not found at: {tesseract_path}")
            logging.error(
                "Please install Tesseract OCR and/or configure the correct path."
            )
            sys.exit(1)

    generate_context(args.basefolder, args.output_folder)
