# This script is a utility designed to scan a directory of AMA (Ask Me Anything)
# session folders to identify which sessions are missing their corresponding
# transcript and/or summary files. It provides a clear report of the status of
# all sessions and can generate a list of sessions that require processing.
#
# The script's core functionalities include:
# 1.  **Folder Scanning**: It systematically iterates through numbered subdirectories
#     (e.g., '01-', '02-') within a specified root data folder. Within each of
#     these, it looks for an 'Ask Me Anything' subdirectory where the session
#     recordings are stored.
#
# 2.  **Video File Discovery**: It identifies all video files (based on a list of
#     common video extensions) within the 'Ask Me Anything' subdirectory. This
#     allows for multiple video sessions to exist within a single parent folder.
#
# 3.  **Completion Check**: For each video file found, it checks for the existence
#     of two key output files: 'Meeting Recording_transcript.txt' and
#     'Meeting Recording_summary.txt'. The presence or absence of these files
#     determines the completion status of the session.
#
# 4.  **Detailed Reporting**: The script prints a detailed, real-time log to the
#     console as it scans, showing the status of each video session in each
#     folder. It then generates a comprehensive summary report that categorizes
#     sessions into:
#     - Complete (both transcript and summary exist)
#     - Missing both files
#     - Missing only the transcript
#     - Missing only the summary
#
# 5.  **Exporting a "To-Process" List**: An optional command-line flag (`--list-missing`)
#     allows the user to generate a clean, formatted list of all sessions that are
#     missing at least one of the required files. This list can be used to inform
#     a batch processing script (like `process_missing_sessions.py`).
#
# 6.  **Modular Functions**: The script is structured with clear, single-responsibility
#     functions (e.g., `find_video_files`, `check_transcript_summary_exists`,
#     `get_sessions_to_process`), making it easy to import its logic into other
#     scripts in the workflow.
#
# Usage:
#   - To get a full report of all sessions:
#     `python src/scan_missing_sessions.py`
#   - To get a report and also list the files that need processing:
#     `python src/scan_missing_sessions.py --list-missing`

#!/usr/bin/env python3

"""
Script to scan all data folders and identify AMA sessions missing transcript/summary files.
"""

import os
from pathlib import Path
from typing import List, Dict
import argparse


def find_video_files(folder_path: Path) -> List[Path]:
    """Find all video files in a folder."""
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}
    video_files = []

    if not folder_path.exists():
        return video_files

    for file_path in folder_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            video_files.append(file_path)

    return video_files


def check_transcript_summary_exists(video_path: Path) -> Dict[str, bool]:
    """Check if transcript and summary files exist for a video."""
    video_dir = video_path.parent

    transcript_file = video_dir / "Meeting Recording_transcript.txt"
    summary_file = video_dir / "Meeting Recording_summary.txt"

    return {
        "transcript_exists": transcript_file.exists(),
        "summary_exists": summary_file.exists(),
        "transcript_path": transcript_file,
        "summary_path": summary_file,
    }


def scan_all_folders(data_root: Path) -> Dict[str, List[Dict]]:
    """Scan all folders in data directory for missing sessions."""
    results = {}

    print(f"🔍 Scanning {data_root} for AMA sessions...")

    # Get all numbered folders (01-, 02-, etc.)
    folders = []
    for item in data_root.iterdir():
        if item.is_dir() and item.name[0].isdigit():
            folders.append(item)

    folders.sort()

    for folder in folders:
        folder_name = folder.name
        print(f"\n📁 Checking folder: {folder_name}")

        # Look for "Ask Me Anything Session Recording" subdirectory
        ama_dir = None
        for subdir in folder.iterdir():
            if subdir.is_dir() and "Ask Me Anything" in subdir.name:
                ama_dir = subdir
                break

        if not ama_dir:
            print(f"   ⚠️ No 'Ask Me Anything' directory found")
            continue

        # Find video files in the AMA directory
        video_files = find_video_files(ama_dir)

        if not video_files:
            print(f"   ⚠️ No video files found in {ama_dir.name}")
            continue

        folder_sessions = []

        for video_file in video_files:
            file_status = check_transcript_summary_exists(video_file)

            session_info = {
                "video_path": video_file,
                "video_name": video_file.name,
                "transcript_exists": file_status["transcript_exists"],
                "summary_exists": file_status["summary_exists"],
                "transcript_path": file_status["transcript_path"],
                "summary_path": file_status["summary_path"],
            }

            folder_sessions.append(session_info)

            # Status indicators
            transcript_status = "✅" if file_status["transcript_exists"] else "❌"
            summary_status = "✅" if file_status["summary_exists"] else "❌"

            print(f"   📹 {video_file.name}")
            print(f"      Transcript: {transcript_status} | Summary: {summary_status}")

        results[folder_name] = folder_sessions

    return results


def print_summary_report(scan_results: Dict[str, List[Dict]]) -> Dict[str, List[str]]:
    """Print a summary report of missing sessions."""
    print(f"\n" + "=" * 80)
    print("📊 SUMMARY REPORT - Missing Transcript/Summary Files")
    print("=" * 80)

    total_sessions = 0
    missing_transcripts = []
    missing_summaries = []
    missing_both = []
    complete_sessions = []

    for folder_name, sessions in scan_results.items():
        for session in sessions:
            total_sessions += 1

            has_transcript = session["transcript_exists"]
            has_summary = session["summary_exists"]

            if not has_transcript and not has_summary:
                missing_both.append(f"{folder_name}: {session['video_name']}")
            elif not has_transcript:
                missing_transcripts.append(f"{folder_name}: {session['video_name']}")
            elif not has_summary:
                missing_summaries.append(f"{folder_name}: {session['video_name']}")
            else:
                complete_sessions.append(f"{folder_name}: {session['video_name']}")

    print(f"\n📈 STATISTICS:")
    print(f"   Total Sessions Found: {total_sessions}")
    print(f"   Complete (both files): {len(complete_sessions)}")
    print(f"   Missing Both: {len(missing_both)}")
    print(f"   Missing Only Transcript: {len(missing_transcripts)}")
    print(f"   Missing Only Summary: {len(missing_summaries)}")

    if missing_both:
        print(
            f"\n❌ SESSIONS MISSING BOTH TRANSCRIPT AND SUMMARY ({len(missing_both)}):"
        )
        for session in missing_both:
            print(f"   • {session}")

    if missing_transcripts:
        print(f"\n📝 SESSIONS MISSING ONLY TRANSCRIPT ({len(missing_transcripts)}):")
        for session in missing_transcripts:
            print(f"   • {session}")

    if missing_summaries:
        print(f"\n📋 SESSIONS MISSING ONLY SUMMARY ({len(missing_summaries)}):")
        for session in missing_summaries:
            print(f"   • {session}")

    return {
        "total_sessions": total_sessions,
        "missing_both": missing_both,
        "missing_transcripts": missing_transcripts,
        "missing_summaries": missing_summaries,
        "complete_sessions": complete_sessions,
    }


def get_sessions_to_process(scan_results: Dict[str, List[Dict]]) -> List[Dict]:
    """Get list of sessions that need processing (missing transcript or summary)."""
    sessions_to_process = []

    for folder_name, sessions in scan_results.items():
        for session in sessions:
            if not session["transcript_exists"] or not session["summary_exists"]:
                session["folder_name"] = folder_name
                sessions_to_process.append(session)

    return sessions_to_process


def main():
    parser = argparse.ArgumentParser(
        description="Scan for missing AMA session transcripts/summaries"
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="data",
        help="Root directory containing session folders (default: data)",
    )
    parser.add_argument(
        "--list-missing",
        action="store_true",
        help="List all missing sessions for processing",
    )

    args = parser.parse_args()

    data_root = Path(args.data_root)
    if not data_root.exists():
        print(f"❌ Data root directory not found: {data_root}")
        return

    # Scan all folders
    scan_results = scan_all_folders(data_root)

    # Print summary report
    summary = print_summary_report(scan_results)

    # If requested, list sessions that need processing
    if args.list_missing:
        sessions_to_process = get_sessions_to_process(scan_results)
        print(f"\n🎯 SESSIONS TO PROCESS ({len(sessions_to_process)}):")
        print("=" * 80)

        for i, session in enumerate(sessions_to_process, 1):
            transcript_needed = "📝" if not session["transcript_exists"] else ""
            summary_needed = "📋" if not session["summary_exists"] else ""

            print(f"{i:2d}. {session['folder_name']}")
            print(f"    📹 {session['video_name']}")
            print(f"    🎯 Need: {transcript_needed} {summary_needed}")
            print(f"    📂 {session['video_path']}")
            print()


if __name__ == "__main__":
    main()
