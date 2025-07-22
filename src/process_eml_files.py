import os
import email
from email import policy
from email.parser import BytesParser
import glob
from pathlib import Path


def process_eml_files(eml_directory, output_directory):
    """
    Processes all .eml files in a directory, extracting the email body and attachments.

    For each .eml file, it creates a subdirectory in the output_directory named after the
    .eml file's base name. Inside this new subdirectory, it saves the email's body as
    'email.txt' and any attachments with their original filenames.

    Args:
        eml_directory (str): The path to the directory containing the .eml files.
        output_directory (str): The path to the directory where the output folders will be created.
    """
    eml_pattern = os.path.join(eml_directory, "*.eml")
    eml_files = glob.glob(eml_pattern)

    if not eml_files:
        print(f"No .eml files found in '{eml_directory}'")
        return

    print(f"Found {len(eml_files)} .eml files to process.")

    for eml_path in eml_files:
        base_filename = Path(eml_path).stem.strip()
        target_folder = Path(output_directory) / base_filename

        try:
            target_folder.mkdir(parents=True, exist_ok=True)
            print(f"Created folder: {target_folder}")

            with open(eml_path, "rb") as fp:
                msg = BytesParser(policy=policy.default).parse(fp)

            # Save the email body
            body = msg.get_body(preferencelist=("plain", "html"))
            if body:
                email_content = body.get_content()
                with open(target_folder / "email.txt", "w", encoding="utf-8") as f:
                    f.write(email_content)
                print(f"  - Saved email.txt")

            # Save attachments
            attachment_count = 0
            for part in msg.walk():
                if (
                    part.get_content_maintype() == "multipart"
                    or part.get_content_maintype() == "text"
                ):
                    continue

                if part.get("content-disposition") is None:
                    continue

                filename = part.get_filename()
                if filename:
                    attachment_path = target_folder / filename
                    with open(attachment_path, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    print(f"  - Saved attachment: {filename}")
                    attachment_count += 1

            if attachment_count == 0:
                print("  - No attachments found.")

        except FileNotFoundError:
            print(f"Error: The system cannot find the file specified for {eml_path}.")
        except OSError as e:
            print(f"OSError processing {eml_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {eml_path}: {e}")


if __name__ == "__main__":
    # Using raw string for the path to handle backslashes correctly on Windows
    eml_dir = r"C:\Users\fbrun\Documents\GitHub\ZurichInnovation\data\06- Underwriting- Mid Market-  Australia\Data\Additional Samples"
    output_dir = (
        r"C:\Users\fbrun\Documents\GitHub\ZurichInnovation\output\eml_extractions"
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    process_eml_files(eml_dir, output_dir)
    print("\nProcessing complete.")
