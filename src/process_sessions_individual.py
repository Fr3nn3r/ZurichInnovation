# This script is designed to process a predefined list of "missing" AMA (Ask Me Anything)
# sessions. It iterates through a hardcoded list of sessions, each defined by a
# folder and a video filename, and processes them one by one.
#
# The main functionalities of this script are:
# 1.  **Session Identification**: It uses a `MISSING_SESSIONS` list to identify which
#     video files need processing. It constructs the full path to each video file
#     by searching within 'Ask Me Anything' subdirectories inside the specified
#     session folder.
#
# 2.  **Completion Check**: Before processing, it checks if a session is already
#     complete by verifying the existence of both a transcript and a summary file
#     ('Meeting Recording_transcript.txt' and 'Meeting Recording_summary.txt').
#     If both files exist, the session is skipped.
#
# 3.  **Individual Processing**: For each session that is not complete, it invokes
#     another script, `process_video.py`, as a subprocess to handle the actual
#     transcription and summarization. This allows for modular processing and
#     clear separation of concerns.
#
# 4.  **Retry Logic**: If the processing of a video fails (i.e., the subprocess
#     returns a non-zero exit code), the script will automatically retry the
#     processing up to a defined maximum number of attempts, with a short delay
#     between retries.
#
# 5.  **Progress Tracking and Reporting**: The script provides detailed, real-time
#     feedback to the user, including which session is being processed, whether it
#     is being skipped, the status of transcript and summary creation, and the
#     final outcome of the processing. It concludes with a summary report of
#     successful, skipped, and failed sessions.
#
# 6.  **Command-Line Control**: It includes command-line arguments to specify the
#     root data directory, start processing from a specific session number, or
#     process only a single, specified session, offering flexibility in how the
#     processing is run.
#
# Usage:
#   - To run all missing sessions:
#     `python src/process_sessions_individual.py`
#   - To start from the 3rd session in the list:
#     `python src/process_sessions_individual.py --start-from 3`
#   - To process only the 5th session:
#     `python src/process_sessions_individual.py --only-session 5`

#!/usr/bin/env python3

"""
Script to process missing AMA sessions one by one with detailed progress tracking.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict
import argparse


# List of missing sessions based on scan results
MISSING_SESSIONS = [
    {
        "folder": "05- Claims- Liability Decisions- Canada",
        "video": "Follow-Up AMA Session Liability decisions in complex claims – Agentic AI HyperChallenge-20250704_153336-Meeting Recording.mp4",
    },
    {
        "folder": "07- Underwriting- SME- UK",
        "video": "Follow-Up AMA Session Small Business- Broker Underwriting Interaction Agent – Agentic AI HyperChallenge-20250704_133239-Meeting Recording.mp4",
    },
    {
        "folder": "08- Underwriting- Business Mix And Performance -UK",
        "video": "Follow-Up AMA Session Business Mix And Performance -UK – Agentic AI HyperChallenge-20250704_130218-Meeting Recording.mp4",
    },
    {
        "folder": "09- Underwriting- Bond-  Germany",
        "video": "Follow-Up AMA Session Bond Intelligence Transforming Contract Review Through AI-Assisted Underwriting – Agentic AI HyperChallenge-20250708_153235-Meeting Recording.mp4",
    },
    {
        "folder": "11- Underwriting- Trade Credit- Germany",
        "video": "Follow-Up AMA Session Trade Credit Accelerator AI-Enabled Top-Up Policy Evaluation  – Agentic AI HyperChallenge-20250707_133211-Meeting Recording.mp4",
    },
    {
        "folder": "13- Marketing - SEO Website Manager - Switzerland",
        "video": "Follow-Up AMA Session Agentic AI SEOWebsite manager – Agentic AI HyperChallenge-20250708_110123-Meeting Recording.mp4",
    },
    {
        "folder": "14- Marketing - Performance Manager - Switzerland",
        "video": "Follow-Up AMA Session Agentic AI Performance Campaign Manager – Agentic AI HyperChallenge-20250708_090302-Meeting Recording.mp4",
    },
    {
        "folder": "17- Finance- Reporting Pipelines- Switzerland",
        "video": "Follow-Up AMA Session Agent-Oriented Reporting Pipelines – Agentic AI HyperChallenge-20250707_150219-Meeting Recording (1).mp4",
    },
]


def find_video_path(folder_name: str, video_name: str, data_root: Path) -> Path:
    """Find the full path to a video file."""
    folder_path = data_root / folder_name

    # Look for Ask Me Anything directories
    ama_dirs = []
    for subdir in folder_path.iterdir():
        if subdir.is_dir() and "Ask Me Anything" in subdir.name:
            ama_dirs.append(subdir)

    for ama_dir in ama_dirs:
        video_path = ama_dir / video_name
        if video_path.exists():
            return video_path

    raise FileNotFoundError(f"Video not found: {video_name} in {folder_name}")


def check_session_completion(
    folder_name: str, video_name: str, data_root: Path
) -> Dict[str, bool]:
    """Check if a session has been completed (has both transcript and summary)."""
    try:
        video_path = find_video_path(folder_name, video_name, data_root)
        video_dir = video_path.parent

        transcript_file = video_dir / "Meeting Recording_transcript.txt"
        summary_file = video_dir / "Meeting Recording_summary.txt"

        return {
            "transcript_exists": transcript_file.exists(),
            "summary_exists": summary_file.exists(),
            "video_path": video_path,
        }
    except FileNotFoundError:
        return {"transcript_exists": False, "summary_exists": False, "video_path": None}


def process_single_session_with_retry(video_path: Path, max_retries: int = 2) -> bool:
    """Process a single session with retry logic."""
    for attempt in range(max_retries):
        try:
            print(
                f"\n🎬 Processing attempt {attempt + 1}/{max_retries}: {video_path.name}"
            )
            print(f"📂 Location: {video_path.parent}")

            start_time = time.time()

            # Run the process_video.py script
            result = subprocess.run(
                [sys.executable, "src/process_video.py", str(video_path)],
                capture_output=False,  # Allow real-time output
                text=True,
                cwd=Path.cwd(),
            )

            elapsed_time = time.time() - start_time

            if result.returncode == 0:
                print(
                    f"✅ Session processed successfully in {elapsed_time:.1f} seconds!"
                )
                return True
            else:
                print(f"❌ Processing failed with return code {result.returncode}")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 5 seconds...")
                    time.sleep(5)

        except Exception as e:
            print(f"❌ Exception during processing: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in 5 seconds...")
                time.sleep(5)

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Process missing AMA sessions individually"
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="data",
        help="Root directory containing session folders (default: data)",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="Start processing from session number (1-based, default: 1)",
    )
    parser.add_argument(
        "--only-session",
        type=int,
        help="Process only a specific session number (1-based)",
    )

    args = parser.parse_args()

    data_root = Path(args.data_root)
    if not data_root.exists():
        print(f"❌ Data root directory not found: {data_root}")
        return

    # Filter sessions to process
    sessions_to_process = MISSING_SESSIONS.copy()

    if args.only_session:
        if 1 <= args.only_session <= len(MISSING_SESSIONS):
            sessions_to_process = [MISSING_SESSIONS[args.only_session - 1]]
        else:
            print(
                f"❌ Invalid session number. Must be between 1 and {len(MISSING_SESSIONS)}"
            )
            return
    elif args.start_from > 1:
        sessions_to_process = MISSING_SESSIONS[args.start_from - 1 :]

    print(f"🎯 PROCESSING {len(sessions_to_process)} SESSIONS")
    print("=" * 80)

    results = {}
    successful = 0
    failed = 0
    skipped = 0

    for i, session in enumerate(sessions_to_process, 1):
        folder_name = session["folder"]
        video_name = session["video"]

        print(f"\n[{i}/{len(sessions_to_process)}] 📁 {folder_name}")
        print("-" * 80)

        # Check if session is already completed
        status = check_session_completion(folder_name, video_name, data_root)

        if status["transcript_exists"] and status["summary_exists"]:
            print("✅ Session already completed, skipping...")
            results[folder_name] = True
            skipped += 1
            continue

        if status["video_path"] is None:
            print("❌ Video file not found, skipping...")
            results[folder_name] = False
            failed += 1
            continue

        # Indicate what needs to be done
        transcript_needed = "📝" if not status["transcript_exists"] else ""
        summary_needed = "📋" if not status["summary_exists"] else ""
        print(f"🎯 Need: {transcript_needed} {summary_needed}")

        # Process the session
        success = process_single_session_with_retry(status["video_path"])
        results[folder_name] = success

        if success:
            successful += 1
        else:
            failed += 1

    # Final summary
    print(f"\n" + "=" * 80)
    print("📊 PROCESSING SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {successful}")
    print(f"⏭️ Skipped (already complete): {skipped}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(sessions_to_process)}")

    if failed > 0:
        print(f"\n❌ Failed sessions:")
        for folder_name, success in results.items():
            if not success:
                print(f"   • {folder_name}")

    print(f"\n🎉 Processing completed!")


if __name__ == "__main__":
    main()
