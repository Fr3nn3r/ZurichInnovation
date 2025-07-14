import os
import sys
import json
import logging
import argparse
import base64
import mimetypes
import io
import re
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import pandas as pd
import pypdfium2 as pdfium

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


def is_ocr_gibberish(text: str) -> bool:
    """
    Detects if the OCR output is sparse or gibberish based on simple rules.
    """
    clean_text = text.strip()

    if not clean_text or len(clean_text) < 50:  # If the text is empty or very short
        return True

    # Check the ratio of alphanumeric characters to total characters
    alphanum_chars = sum(c.isalnum() for c in clean_text)
    total_chars = len(clean_text)

    if total_chars > 0 and (alphanum_chars / total_chars) < 0.6:
        return True  # Less than 60% alphanumeric characters suggests gibberish

    return False


def extract_json_from_output(raw_output: str) -> Dict[str, Any]:
    """
    Extracts and parses JSON from a raw string, cleaning up markdown code blocks.
    """
    # Remove Markdown code block if present
    match = re.search(r"```json(.*?)```", raw_output, re.DOTALL | re.IGNORECASE)
    if match:
        json_str = match.group(1).strip()
    else:
        # fallback: try to find the first '{' and last '}'
        start = raw_output.find("{")
        end = raw_output.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = raw_output[start : end + 1]
        else:
            raise ValueError("No JSON found in output")
    # Parse JSON
    return json.loads(json_str)


def encode_image_to_base64(file_path: Path) -> str:
    """Encodes an image file to a base64 string."""
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_with_vision(client: OpenAI, image_base64: str) -> str:
    """
    Generates a description or extracts structured data from an image using the
    OpenAI Vision API with the new universal prompt.
    """
    new_prompt = """
You are an AI assistant for universal document and image processing.
For the image provided:

If the image is a document (receipt, ticket, invoice, form, etc.), extract all visible information in structured JSON format (include key fields, tables, totals, dates, etc.).

If the image is a photo (e.g., a vehicle, damaged property, or objects), describe the content and any visible details as clearly as possible.

In all cases, identify the type of image or document, and include this as a field in your output.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": new_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }
        ],
        max_tokens=2048,
    )
    return response.choices[0].message.content


def process_pdf_with_vision(client: OpenAI, file_path: Path) -> List[Dict[str, Any]]:
    """
    Processes a PDF page-by-page using the Vision API.
    Used as a fallback when Tesseract OCR fails.
    """
    results = []
    logging.info(f"Processing PDF {file_path.name} with Vision API fallback...")
    try:
        pdf_doc = pdfium.PdfDocument(file_path)
        for i, page in enumerate(pdf_doc):
            logging.info(f"  - Analyzing page {i + 1}/{len(pdf_doc)}...")
            # Render page to a PIL image
            bitmap = page.render(scale=2)  # Scale can be adjusted
            pil_image = bitmap.to_pil()

            # Convert PIL image to base64
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # Analyze the image of the page
            vision_output_str = ""
            try:
                vision_output_str = analyze_with_vision(client, img_base64)
                vision_output_json = extract_json_from_output(vision_output_str)
                results.append(vision_output_json)
            except (ValueError, json.JSONDecodeError) as e:
                logging.warning(
                    f"    - Could not parse JSON from Vision API for page {i + 1}: {e}. Storing raw output."
                )
                results.append(
                    {"error": "Invalid JSON from API", "raw_output": vision_output_str}
                )
            except Exception as e:
                logging.error(f"    - Vision API analysis failed for page {i + 1}: {e}")
                results.append({"error": "Vision API call failed", "details": str(e)})
        return results
    except Exception as e:
        logging.error(f"Failed to process PDF {file_path} with Vision API: {e}")
        return [{"error": "PDF processing with Vision failed", "details": str(e)}]


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
                ocr_text = process_pdf_ocr_only(str(file_path))
                if is_ocr_gibberish(ocr_text):
                    logging.warning(
                        f"Sparse OCR for {relative_path}. Falling back to Vision API."
                    )
                    if client:
                        content = process_pdf_with_vision(client, file_path)
                    else:
                        logging.error(
                            "Cannot use Vision API fallback for PDF as OPENAI_API_KEY is not configured."
                        )
                        content = {"error": "OCR failed and Vision API not available."}
                else:
                    content = ocr_text
            elif file_type == "image":
                if client:
                    vision_output_str = ""
                    try:
                        image_base64 = encode_image_to_base64(file_path)
                        vision_output_str = analyze_with_vision(client, image_base64)
                        content = extract_json_from_output(vision_output_str)
                    except (ValueError, json.JSONDecodeError) as e:
                        logging.warning(
                            f"Could not parse JSON from Vision API for image {relative_path}: {e}. Storing raw output."
                        )
                        content = {
                            "error": "Invalid JSON from API",
                            "raw_output": vision_output_str,
                        }
                    except Exception as e:
                        logging.error(
                            f"Vision API analysis failed for image {relative_path}: {e}"
                        )
                        content = {"error": "Vision API call failed", "details": str(e)}
                else:
                    logging.warning(
                        f"Skipping AI description for {relative_path} due to missing API key."
                    )
                    # Fallback to just OCR if vision is not available
                    content = {
                        "ai_description": "",
                        "ocr_text": get_image_ocr_text(file_path),
                    }

            elif file_type == "text":
                content = read_text_file(file_path)
            elif file_type == "sheet":
                content = read_sheet_file(file_path)
            else:
                logging.warning(f"Unsupported file type for {relative_path}. Skipping.")
                continue

            if content is not None:
                entry["content"] = content
                all_files_context.append(entry)
            else:
                logging.warning(
                    f"Skipping {relative_path} due to content extraction failure."
                )

        except Exception as e:
            logging.error(f"An unexpected error occurred processing {relative_path}:")
            logging.error(traceback.format_exc())
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
        default="output",
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
