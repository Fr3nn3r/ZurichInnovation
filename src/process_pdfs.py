# This script provides a robust solution for extracting text from PDF documents
# using a hybrid approach that combines direct text extraction with Optical
# Character Recognition (OCR). It is designed to handle a variety of PDF types,
# including those with embedded text and those that are purely image-based.
#
# The script's main functionalities are:
# 1.  **Hybrid Text Extraction**: For each page in a PDF, it first attempts to
#     extract text directly using the `pdfplumber` library. This method is fast
#     and accurate for PDFs with embedded, machine-readable text.
#
# 2.  **Noise Detection and OCR Fallback**: If the text extracted by `pdfplumber`
#     is empty or contains a significant amount of "noise" (specifically, `(cid:XX)`
#     artifacts that indicate font encoding issues), the script automatically
#     falls back to a more robust OCR-based method for that page.
#
# 3.  **Page-level OCR**: In the fallback scenario, the script renders the specific
#     page into a high-resolution image and then uses the Tesseract OCR engine
#     to extract the text from the image.
#
# 4.  **Full OCR Fallback**: If `pdfplumber` fails to open or process a PDF file
#     entirely, the script has a secondary fallback mechanism that uses `pypdfium2`
#     to render every page to an image and process the entire document with OCR.
#
# 5.  **Image Preprocessing**: Before any OCR is performed, the rendered page images
#     are preprocessed. They are converted to grayscale and then to a binary
#     (black and white) format to improve the accuracy of the Tesseract engine.
#
# 6.  **Text Cleaning**: All extracted text, whether from direct extraction or OCR,
#     is cleaned to remove the `(cid:XX)` artifacts and to normalize whitespace,
#     ensuring a cleaner final output.
#
# 7.  **Batch Processing**: The `main` function orchestrates the processing of
#     multiple case folders. It iterates through subdirectories in a specified
#     input folder, processes all PDFs within each, aggregates the cleaned text,
#     and saves it to a single `-context.txt` file per case folder in an
#     output directory.
#
# Note:
#   This script requires that the Tesseract OCR engine is installed on the system.
#   The path to the executable may need to be configured within the script,
#   especially on Windows.

import os
import pytesseract
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageOps
import io
import re

# NOTE: Tesseract OCR must be installed on the system for this script to work.
# On Windows, you can download and install it from: https://github.com/UB-Mannheim/tesseract/wiki
# You may need to configure the path to the Tesseract executable.
# For example: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def preprocess_image_for_ocr(pil_image):
    """
    Pre-processes a PIL image for better OCR results using Pillow.
    - Converts to grayscale
    - Converts to black and white (binarization)
    """
    # Convert the image to gray scale
    gray_image = ImageOps.grayscale(pil_image)

    # Convert to black and white
    # The '1' mode is a 1-bit-per-pixel image, which is what we need for binarization.
    binary_image = gray_image.convert("1")

    return binary_image


def ocr_pdf_page(page_image):
    """
    Performs OCR on a single PDF page image after pre-processing it.
    """
    preprocessed_image = preprocess_image_for_ocr(page_image)
    return pytesseract.image_to_string(preprocessed_image)


def clean_text(text):
    """
    Cleans the extracted text by removing CID font artifacts and extra whitespace.
    """
    # Remove (cid:XX) patterns
    text = re.sub(r"\(cid:\d+\)", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def has_significant_noise(text, threshold=0.1):
    """
    Checks if the text contains a significant amount of CID noise.
    """
    noise_chars = len(re.findall(r"\(cid:\d+\)", text))
    total_chars = len(text)
    if total_chars == 0:
        return False

    noise_ratio = (
        noise_chars * 7
    ) / total_chars  # Approximate length of a (cid:X) pattern
    return noise_ratio > threshold


def process_pdf(file_path):
    """
    Processes a single PDF file, extracting text using pdfplumber and falling back to
    a more robust OCR method if the direct extraction is noisy or empty.
    """
    full_text = []

    # Attempt to extract text with pdfplumber first
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                extracted_text = page.extract_text()

                # If text is empty or contains significant noise, use OCR
                if not extracted_text or has_significant_noise(extracted_text):
                    print(
                        f"  - Page {page_num}: Noisy or empty text from pdfplumber, falling back to OCR."
                    )
                    # Render page to an image
                    page_image = page.to_image(resolution=300).original
                    page_text = ocr_pdf_page(page_image)
                else:
                    page_text = extracted_text

                full_text.append(clean_text(page_text))
        return "\n".join(full_text)
    except Exception as e:
        print(
            f"Could not process {file_path} with pdfplumber, falling back to full OCR. Error: {e}"
        )

    # Fallback to full OCR with pypdfium2 if pdfplumber fails entirely
    try:
        full_text = []
        doc = pdfium.PdfDocument(file_path)
        for i in range(len(doc)):
            page = doc.get_page(i)
            bitmap = page.render(scale=3)  # render with a higher scale for better OCR
            pil_image = Image.frombytes(
                "RGB", [bitmap.width, bitmap.height], bitmap.buffer
            )
            page_text = ocr_pdf_page(pil_image)
            full_text.append(clean_text(page_text))
        return "\n".join(full_text)
    except Exception as e:
        print(f"Failed to process {file_path} with OCR. Error: {e}")
        return ""


def main():
    """
    Main function to iterate through case folders, process PDFs, and save the text.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(base_dir, "Canada - Liability decisions data files")
    output_dir = os.path.join(base_dir, "output")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process only a subset of case folders for demonstration if needed
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
            text = process_pdf(pdf_path)
            all_case_text.append(f"--- Content from: {pdf_file} ---\n{text}\n\n")

        if all_case_text:
            output_filename = f"{case_name}-context.txt"
            output_filepath = os.path.join(output_dir, output_filename)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write("".join(all_case_text))
            print(f"  => Saved context to {output_filepath}")


if __name__ == "__main__":
    main()
