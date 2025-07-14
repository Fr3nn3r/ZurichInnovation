import os
import subprocess
import sys


def run_calibration_on_directory(directory_path, output_filename):
    """
    Finds all .docx.txt files in a directory and runs the evaluation script in training mode.
    """
    print(f"--- Processing files in: {directory_path} for calibration ---")

    # Remove old training file if it exists
    if os.path.exists(output_filename):
        os.remove(output_filename)
        print(f"Removed old '{output_filename}' to generate fresh data.")

    for filename in os.listdir(directory_path):
        if filename.endswith(".docx.txt"):
            file_path = os.path.join(directory_path, filename)
            print(f"  - Evaluating: {filename}")
            try:
                # We call evaluate_file.py as a separate process in training mode
                result = subprocess.run(
                    [
                        sys.executable,
                        "src/evaluate_file.py",
                        file_path,
                        "--generate-training-data",
                        "--output-file",
                        output_filename,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"Failed to evaluate {file_path} for training.")
                    print(f"Stderr: {result.stderr}")
                    print(f"Stdout: {result.stdout}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to evaluate {file_path} for training.")
                print(f"Stderr: {e.stderr}")
                print(f"Stdout: {e.stdout}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python run_all_for_calibration.py <good_data_dir> <bad_data_dir>")
        sys.exit(1)

    good_data_dir = sys.argv[1]
    bad_data_dir = sys.argv[2]

    run_calibration_on_directory(good_data_dir, "output/training_scores_good.json")
    run_calibration_on_directory(bad_data_dir, "output/training_scores_bad.json")

    print("\\n--- All calibration data generated. ---")
