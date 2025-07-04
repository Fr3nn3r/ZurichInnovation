import os
import subprocess
import sys


def run_evaluations_on_directory(directory_path):
    """
    Finds all .docx.txt files in a directory and runs the evaluation script on them.
    """
    print(f"--- Processing files in: {directory_path} ---")
    if not os.path.exists("output"):
        os.makedirs("output")

    for filename in os.listdir(directory_path):
        if filename.endswith(".docx.txt"):
            file_path = os.path.join(directory_path, filename)
            print(f"Evaluating: {file_path}")
            try:
                # We call evaluate_file.py as a separate process
                subprocess.run(
                    [sys.executable, "src/evaluate_file.py", file_path],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"Failed to evaluate {file_path}.")
                print(f"Stderr: {e.stderr}")
                print(f"Stdout: {e.stdout}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_evaluations.py <directory1> <directory2> ...")
        sys.exit(1)

    for directory in sys.argv[1:]:
        run_evaluations_on_directory(directory)

    print("\\n--- All evaluations complete. ---")
