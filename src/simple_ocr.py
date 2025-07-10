import os
import sys
import subprocess

# Ensure required packages are installed
required_packages = [
    "pytesseract",
    "pypdfium2",
    "pillow",  # Provides PIL
]


def install_packages():
    for pkg in required_packages:
        try:
            __import__(pkg if pkg != "pillow" else "PIL")
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


install_packages()

import pytesseract
import pypdfium2 as pdfium
from PIL import Image, ImageOps
import re

# NOTE: Tesseract OCR must be installed on the system for this script to work.
# On Windows, you can download and install it from: https://github.com/UB-Mannheim/tesseract/wiki
# You may need to configure the path to the Tesseract executable.
# For example: pytesseract.pytesseract.tesseract_cmd = r'"C:\Program Files\Tesseract-OCR\tesseract.exe"'

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def preprocess_image_for_ocr(pil_image):
    """
    Pre-processes a PIL image for better OCR results using Pillow.
    """
    gray_image = ImageOps.grayscale(pil_image)
    binary_image = gray_image.convert("1")
    return binary_image


def clean_text(text):
    """
    Cleans the extracted text by removing extra whitespace.
    """
    return re.sub(r"\s+", " ", text).strip()


def process_pdf_ocr_only(file_path):
    """
    Processes a single PDF file using a pure OCR approach with pypdfium2 and Tesseract.
    """
    full_text = []
    try:
        doc = pdfium.PdfDocument(file_path)
        for i in range(len(doc)):
            page = doc.get_page(i)
            # Render with a high resolution for better OCR
            bitmap = page.render(scale=3)
            pil_image = bitmap.to_pil()

            preprocessed_image = preprocess_image_for_ocr(pil_image)
            page_text = pytesseract.image_to_string(preprocessed_image)

            full_text.append(clean_text(page_text))
        return "\n".join(full_text)
    except Exception as e:
        print(f"  - Failed to process {file_path} with OCR. Error: {e}")
        return ""


def main():
    """
    Main function to iterate through case folders, process PDFs, and save the text.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Allow custom input and output directories via CLI args
    # Usage: python simple_ocr.py [input_dir] [output_dir]
    # If not provided, fall back to original defaults.
    args = sys.argv[1:]
    if len(args) >= 1:
        input_dir = os.path.abspath(args[0])
    else:
        input_dir = os.path.join(base_dir, "Canada - Liability decisions data files")

    if len(args) >= 2:
        output_dir = os.path.abspath(args[1])
    else:
        output_dir = os.path.join(base_dir, "output")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_case_folders = [
        d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))
    ]

    for case_folder in all_case_folders:
        case_path = os.path.join(input_dir, case_folder)
        case_name = os.path.basename(case_path).replace(" ", "-")
        print(f"Processing case: {case_name}")

        all_case_text = []
        pdf_files = [f for f in os.listdir(case_path) if f.lower().endswith(".pdf")]

        for pdf_file in pdf_files:
            pdf_path = os.path.join(case_path, pdf_file)
            print(f"  - Processing file: {pdf_file}")
            text = process_pdf_ocr_only(pdf_path)
            all_case_text.append(f"--- Content from: {pdf_file} ---\n{text}\n\n")

        if all_case_text:
            output_filename = f"{case_name}-context-clean.txt"
            output_filepath = os.path.join(output_dir, output_filename)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write("".join(all_case_text))
            print(f"  => Saved cleaned context to {output_filepath}")


if __name__ == "__main__":
    main()
