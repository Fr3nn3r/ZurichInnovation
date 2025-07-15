# This script is a dedicated Optical Character Recognition (OCR) tool for
# processing PDF documents. It is designed to iterate through a directory of case
# folders, extract text from all PDF files within each folder using the Tesseract
# OCR engine, and then save the aggregated text into a single, clean context file
# for each case.
#
# The script's main functionalities are:
# 1.  **Dependency Management**: It includes a function to check for and install
#     necessary Python packages, including `pytesseract` for the OCR interface,
#     `pypdfium2` for PDF rendering, and `Pillow` for image manipulation.
#
# 2.  **PDF-to-Image Conversion**: It uses `pypdfium2` to render each page of a
#     PDF document into a high-resolution image. This is a crucial step as
#     Tesseract operates on images, not directly on PDF files.
#
# 3.  **Image Preprocessing**: Before performing OCR, each rendered page (as a
#     Pillow image object) is preprocessed to improve the accuracy of the text
#     extraction. This includes converting the image to grayscale and then to a
#     binary (black and white) format, which often yields better results with
#     Tesseract.
#
# 4.  **OCR with Tesseract**: The preprocessed image of each page is then passed
#     to the `pytesseract` library, which interfaces with the Tesseract engine
#     to extract the text content.
#
# 5.  **Text Cleaning and Aggregation**: The raw text extracted from each page is
#     cleaned to remove extra whitespace. The cleaned text from all pages and all
#     PDFs within a single case folder is then aggregated into one string, with
#     headers indicating the source file for each block of content.
#
# 6.  **Context File Generation**: The final aggregated text for each case folder
#     is saved to a `-context-clean.txt` file in a specified output directory.
#
# 7.  **Command-Line Interface**: The script can be run with optional command-line
#     arguments to specify the input directory (containing the case folders) and
#     the output directory. If no arguments are provided, it defaults to a
#     pre-defined folder structure.
#
# Note:
#   This script requires that the Tesseract OCR engine is installed on the system.
#   On Windows, the path to the `tesseract.exe` executable is hardcoded and may
#   need to be adjusted depending on the installation location.

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
