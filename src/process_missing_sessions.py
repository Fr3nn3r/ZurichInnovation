#!/usr/bin/env python3

"""
Script to process all missing AMA sessions (transcripts and summaries).
Uses the improved video processing script with GPT-4 chunking support.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict
import argparse
from scan_missing_sessions import scan_all_folders, get_sessions_to_process


def process_single_session(video_path: Path) -> bool:
    """Process a single video session using the process_video.py script."""
    try:
        print(f"\n🎬 Processing: {video_path.name}")
        print(f"📂 Location: {video_path.parent}")

        # Run the process_video.py script
        result = subprocess.run(
            [sys.executable, "src/process_video.py", str(video_path)],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            print("✅ Session processed successfully!")
            return True
        else:
            print(f"❌ Processing failed with return code {result.returncode}")
            if result.stdout:
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
            if result.stderr:
                print("STDERR:", result.stderr[-500:])  # Last 500 chars
            return False

    except Exception as e:
        print(f"❌ Exception during processing: {e}")
        return False


def process_missing_sessions(
    data_root: Path, session_filter: str = None
) -> Dict[str, bool]:
    """Process all missing sessions or sessions matching a filter."""
    print(f"🔍 Scanning for missing sessions in {data_root}...")

    # Get scan results
    scan_results = scan_all_folders(data_root)
    sessions_to_process = get_sessions_to_process(scan_results)

    if not sessions_to_process:
        print("✅ No missing sessions found! All sessions have been processed.")
        return {}

    # Apply filter if provided
    if session_filter:
        sessions_to_process = [
            session
            for session in sessions_to_process
            if session_filter.lower() in session["folder_name"].lower()
        ]

        if not sessions_to_process:
            print(f"🔍 No sessions found matching filter: {session_filter}")
            return {}

    print(f"\n🎯 Found {len(sessions_to_process)} sessions to process:")
    for i, session in enumerate(sessions_to_process, 1):
        transcript_needed = "📝" if not session["transcript_exists"] else ""
        summary_needed = "📋" if not session["summary_exists"] else ""
        print(
            f"  {i:2d}. {session['folder_name']}: {transcript_needed} {summary_needed}"
        )

    print(f"\n🚀 Starting batch processing...")
    print("=" * 80)

    results = {}
    successful = 0
    failed = 0

    for i, session in enumerate(sessions_to_process, 1):
        folder_name = session["folder_name"]
        video_path = session["video_path"]

        print(f"\n[{i}/{len(sessions_to_process)}] 📁 {folder_name}")
        print("-" * 60)

        success = process_single_session(video_path)
        results[folder_name] = success

        if success:
            successful += 1
        else:
            failed += 1

    # Final summary
    print(f"\n" + "=" * 80)
    print("📊 BATCH PROCESSING SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(sessions_to_process)}")

    if failed > 0:
        print(f"\n❌ Failed sessions:")
        for folder_name, success in results.items():
            if not success:
                print(f"   • {folder_name}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Process missing AMA session transcripts/summaries"
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="data",
        help="Root directory containing session folders (default: data)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Filter sessions by folder name (case-insensitive substring match)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually processing",
    )

    args = parser.parse_args()

    data_root = Path(args.data_root)
    if not data_root.exists():
        print(f"❌ Data root directory not found: {data_root}")
        return

    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual processing will occur")
        print("=" * 80)

        scan_results = scan_all_folders(data_root)
        sessions_to_process = get_sessions_to_process(scan_results)

        if args.filter:
            sessions_to_process = [
                session
                for session in sessions_to_process
                if args.filter.lower() in session["folder_name"].lower()
            ]

        print(f"\n🎯 Would process {len(sessions_to_process)} sessions:")
        for i, session in enumerate(sessions_to_process, 1):
            transcript_needed = "📝" if not session["transcript_exists"] else ""
            summary_needed = "📋" if not session["summary_exists"] else ""
            print(
                f"  {i:2d}. {session['folder_name']}: {transcript_needed} {summary_needed}"
            )
            print(f"      📹 {session['video_name']}")

        return

    # Process the sessions
    results = process_missing_sessions(data_root, args.filter)

    if results:
        print(f"\n🎉 Batch processing completed!")


if __name__ == "__main__":
    main()
