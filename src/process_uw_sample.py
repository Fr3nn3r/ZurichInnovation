import os
import sys
import subprocess
from pathlib import Path


# --- Dependency Installation ---
def install_dependencies():
    """Install required packages."""
    required = ["pandas", "openpyxl", "pytesseract", "pypdfium2", "pillow", "tqdm"]
    for pkg in required:
        try:
            __import__(
                pkg
                if pkg not in ["pillow", "pytesseract", "pypdfium2"]
                else {
                    "pillow": "PIL",
                    "pytesseract": "pytesseract",
                    "pypdfium2": "pypdfium2",
                }[pkg]
            )
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


install_dependencies()

import pandas as pd
import pytesseract
import pypdfium2 as pdfium
from PIL import Image, ImageOps
from tqdm import tqdm
import re

# Configure Tesseract path if necessary
# On Windows, you might need to set this explicitly.
# Example:
if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


# --- Text and PDF Processing Functions (from simple_ocr.py) ---
def clean_text(text):
    """Removes extra whitespace and optionally other patterns."""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preprocess_image_for_ocr(pil_image):
    """Pre-processes a PIL image for better OCR results."""
    gray_image = ImageOps.grayscale(pil_image)
    return gray_image.convert("1")


def process_pdf_ocr_only(file_path):
    """Processes a single PDF file using a pure OCR approach."""
    full_text = []
    try:
        doc = pdfium.PdfDocument(file_path)
        for i in range(len(doc)):
            page = doc.get_page(i)
            bitmap = page.render(scale=3)
            pil_image = bitmap.to_pil()
            preprocessed_image = preprocess_image_for_ocr(pil_image)
            page_text = pytesseract.image_to_string(preprocessed_image)
            full_text.append(clean_text(page_text))
        return "\n".join(full_text)
    except Exception as e:
        print(f"  - Failed to process {file_path} with OCR. Error: {e}")
        return ""


# --- File Processors ---
def process_text_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading {file_path.name}: {e}"


def process_excel_file(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name=None, header=None)
        content = []
        for sheet_name, sheet_df in df.items():
            content.append(f"--- Sheet: {sheet_name} ---\n")
            content.append(sheet_df.to_csv(index=False, header=False))
        return "\n".join(content)
    except Exception as e:
        return f"Error processing Excel file {file_path.name}: {e}"


def get_file_content(file_path):
    """
    Dispatches file processing based on extension.
    """
    extension = file_path.suffix.lower()
    if extension == ".pdf":
        return process_pdf_ocr_only(file_path)
    elif extension in [".xlsx", ".xls"]:
        return process_excel_file(file_path)
    elif extension in [".txt", ".md", ".json", ".html", ".csv"]:
        return process_text_file(file_path)
    # Add other file types as needed, or ignore them
    return None  # Ignore unsupported file types


def main():
    input_base_dir = Path("Data - New UW Sample")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    if not input_base_dir.is_dir():
        print(f"Error: Input directory '{input_base_dir}' not found.")
        sys.exit(1)

    subfolders = [d for d in input_base_dir.iterdir() if d.is_dir()]

    for folder in tqdm(subfolders, desc="Processing folders"):
        context_content = []
        files_in_folder = list(folder.iterdir())

        for file_path in tqdm(
            files_in_folder, desc=f"Files in {folder.name}", leave=False
        ):
            if file_path.is_file():
                content = get_file_content(file_path)
                if content:
                    context_content.append(f"Filename: {file_path.name}\n")
                    context_content.append(f"{content}\n----\n")

        if context_content:
            output_filename = f"{folder.name}-context.txt"
            output_filepath = output_dir / output_filename

            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write("".join(context_content))
            tqdm.write(f"Created context file: {output_filepath}")

    print("\n--- Processing complete. ---")


if __name__ == "__main__":
    main()
