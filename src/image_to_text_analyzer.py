# This script is a specialized tool for analyzing images, particularly those
# relevant to motor insurance claims. It recursively scans a given directory for
# image files, sends them to the OpenAI Vision API (GPT-4o) for analysis, and
# saves the resulting description to a text file.
#
# The script's main functionalities are:
# 1.  **Dependency Management**: It includes a simple function to check for and
#     install required Python packages (`openai`, `python-dotenv`, `tqdm`) if they
#     are not already present in the environment.
#
# 2.  **Image Discovery**: It walks through a specified input directory and all of
#     its subdirectories to find all image files. It identifies images based on
#     their MIME type, making it robust against a variety of image extensions.
#
# 3.  **OpenAI Vision API Integration**: The script is configured to use the OpenAI
#     API. It encodes each found image into a base64 string and sends it to the
#     `gpt-4o` model.
#
# 4.  **Specialized Prompting**: It uses a specific, carefully crafted prompt that
#     instructs the AI model to analyze the image from the perspective of a motor
#     insurance claim. The prompt asks the model to describe any visible damage
#     to a vehicle, focusing on the type, location, and severity of the damage.
#
# 5.  **Output Generation**: For each image analyzed, the script saves the AI-generated
#     text description into a new text file in a specified output directory. The
#     output filename is derived from the original image filename, with
#     '-damage-analysis.txt' appended.
#
# 6.  **Progress Tracking**: It uses the `tqdm` library to display a progress bar,
#     providing a clear visual indication of how many images have been processed
#     and how many are remaining.
#
# 7.  **Command-Line Interface**: The script is run from the command line, requiring
#     the user to provide an input directory. An optional output directory can also
#     be specified; otherwise, it defaults to a folder named 'output'.
#
# Usage:
#   - To analyze images in a folder and save to the default 'output' directory:
#     `python src/image_to_text_analyzer.py /path/to/image_folder`
#   - To specify a custom output directory:
#     `python src/image_to_text_analyzer.py /path/to/image_folder /path/to/output`

import os
import sys
import subprocess
import base64
import mimetypes
from dotenv import load_dotenv

# --- Package Installation ---
required_packages = ["openai", "python-dotenv", "tqdm"]


def install_packages():
    """Install required Python packages if they are not already installed."""
    for package in required_packages:
        try:
            # A simple import check
            __import__(package if package != "python-dotenv" else "dotenv")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


# Install dependencies before proceeding
install_packages()

from openai import OpenAI
from tqdm import tqdm

# --- Configuration ---
load_dotenv(override=True)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


# --- Main Logic ---
def create_output_directory(output_dir):
    """Create the output directory if it doesn't exist."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")


def is_image_file(filepath):
    """Check if a file is an image based on its MIME type."""
    mimetype, _ = mimetypes.guess_type(filepath)
    return mimetype and mimetype.startswith("image/")


def find_image_files(directory):
    """Recursively find all image files in a directory."""
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            if is_image_file(filepath):
                image_files.append(filepath)
    return image_files


def encode_image_to_base64(filepath):
    """Encode an image file to a base64 string."""
    with open(filepath, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_image_with_openai(client, image_base64, image_path):
    """
    Analyze an image using the OpenAI Vision API with a specific prompt
    to identify vehicle damage.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze the following image of a vehicle and describe any visible damage in detail. Focus on aspects relevant to a motor insurance claim, such as the type, location, and severity of the damage. If no damage is visible, state that clearly.",
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
        return f"Error analyzing {os.path.basename(image_path)}: {e}"


def main():
    """Main function to orchestrate the image analysis process."""
    if len(sys.argv) < 2:
        print(
            "Usage: python image_to_text_analyzer.py <input_directory> [output_directory]"
        )
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY must be set in the .env file.")
        sys.exit(1)

    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' not found.")
        sys.exit(1)

    client = OpenAI(api_key=OPENAI_API_KEY)

    create_output_directory(output_dir)

    print(f"Scanning for images in '{input_dir}'...")
    image_paths = find_image_files(input_dir)

    if not image_paths:
        print("No image files found.")
        return

    print(f"Found {len(image_paths)} images to analyze.")

    with tqdm(total=len(image_paths), desc="Analyzing Images", unit="image") as pbar:
        for image_path in image_paths:
            base_filename = os.path.splitext(os.path.basename(image_path))[0]
            output_filename = f"{base_filename}-damage-analysis.txt"
            output_filepath = os.path.join(output_dir, output_filename)

            image_base64 = encode_image_to_base64(image_path)
            analysis_result = analyze_image_with_openai(
                client, image_base64, image_path
            )

            try:
                with open(output_filepath, "w", encoding="utf-8") as f:
                    f.write(analysis_result)
                tqdm.write(
                    f"Saved analysis for {os.path.basename(image_path)} to {output_filepath}"
                )
            except IOError as e:
                tqdm.write(
                    f"Error saving analysis for {os.path.basename(image_path)}: {e}"
                )

            pbar.update(1)

    print("\n--- Image analysis complete. ---")


if __name__ == "__main__":
    main()
