import os
import argparse
import openai
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import time
import math
import subprocess
from typing import List

# Try importing moviepy with error handling
try:
    from moviepy.editor import VideoFileClip

    print("MoviePy imported successfully")
except ImportError as e:
    print(f"Error importing MoviePy: {e}")
    try:
        import moviepy
        from moviepy.video.io.VideoFileClip import VideoFileClip

        print("MoviePy imported using alternative method")
    except ImportError as e2:
        print(f"Alternative import also failed: {e2}")
        import sys

        sys.exit(1)

# --- Setup ---
load_dotenv(override=True)
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Whisper API file size limit in bytes (25 MB)
WHISPER_FILE_SIZE_LIMIT = 25 * 1024 * 1024


def split_audio_with_ffmpeg(audio_path: Path, max_size_mb=25):
    """
    Split audio file into chunks using ffmpeg directly.
    Returns list of chunk file paths.
    """
    file_size = audio_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size <= max_size_bytes:
        return [audio_path]

    print(
        f"📂 Audio file ({file_size / (1024*1024):.1f} MB) exceeds limit. Splitting into chunks..."
    )

    try:
        # Get audio duration using ffmpeg
        result = subprocess.run(
            ["ffmpeg", "-i", str(audio_path), "-f", "null", "-"],
            capture_output=True,
            text=True,
        )

        # Parse duration from ffmpeg output (duration is in stderr for ffmpeg)
        ffmpeg_output = result.stderr
        duration_line = [
            line for line in ffmpeg_output.split("\n") if "Duration:" in line
        ]
        if not duration_line:
            print("❌ Could not determine audio duration")
            return split_audio_fallback(audio_path, max_size_mb)

        duration_str = duration_line[0].split("Duration: ")[1].split(",")[0]
        h, m, s = duration_str.split(":")
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s)

        # Calculate number of chunks needed (estimate based on file size)
        num_chunks = math.ceil(file_size / max_size_bytes)
        chunk_duration = total_seconds / num_chunks

        chunk_paths = []

        with tqdm(total=num_chunks, desc="Creating audio chunks", unit="chunk") as pbar:
            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunk_path = audio_path.with_name(
                    f"{audio_path.stem}_chunk_{i+1:02d}.mp3"
                )

                # Use ffmpeg to extract chunk
                cmd = [
                    "ffmpeg",
                    "-i",
                    str(audio_path),
                    "-ss",
                    str(start_time),
                    "-t",
                    str(chunk_duration),
                    "-c",
                    "copy",
                    "-y",  # Overwrite output files
                    str(chunk_path),
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    chunk_paths.append(chunk_path)
                else:
                    print(f"❌ Error creating chunk {i+1}: {result.stderr}")

                pbar.update(1)

        print(f"✅ Created {len(chunk_paths)} audio chunks")
        return chunk_paths

    except FileNotFoundError:
        print("❌ ffmpeg not found. Trying fallback method...")
        return split_audio_fallback(audio_path, max_size_mb)
    except Exception as e:
        print(f"❌ Error splitting audio: {e}")
        return split_audio_fallback(audio_path, max_size_mb)


def split_audio_fallback(audio_path: Path, max_size_mb=25):
    """
    Fallback method: Use MoviePy to split by time duration.
    """
    print("⚠️ Using MoviePy fallback method for splitting...")

    try:
        from moviepy.editor import AudioFileClip
    except ImportError:
        import moviepy
        from moviepy.video.io.VideoFileClip import AudioFileClip

    file_size = audio_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    # Estimate duration based on file size ratio
    num_chunks = math.ceil(file_size / max_size_bytes)

    audio_clip = AudioFileClip(str(audio_path))
    total_duration = audio_clip.duration
    chunk_duration = total_duration / num_chunks

    chunk_paths = []

    with tqdm(
        total=num_chunks, desc="Creating audio chunks (fallback)", unit="chunk"
    ) as pbar:
        for i in range(num_chunks):
            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, total_duration)

            chunk_path = audio_path.with_name(f"{audio_path.stem}_chunk_{i+1:02d}.mp3")

            # Extract the chunk and save it
            chunk_clip = audio_clip.subclipped(start_time, end_time)

            # Write to a temporary wav file first, then convert to mp3
            temp_wav = chunk_path.with_suffix(".wav")
            chunk_clip.write_audiofile(str(temp_wav), logger=None)

            # Convert to mp3 using ffmpeg if available, otherwise use the wav
            try:
                subprocess.run(
                    ["ffmpeg", "-i", str(temp_wav), "-y", str(chunk_path)],
                    capture_output=True,
                    check=True,
                )
                temp_wav.unlink()  # Remove temp wav file
                chunk_paths.append(chunk_path)
            except (FileNotFoundError, subprocess.CalledProcessError):
                # If ffmpeg fails, just use the wav file
                chunk_path = temp_wav
                chunk_paths.append(chunk_path)

            chunk_clip.close()
            pbar.update(1)

    audio_clip.close()
    print(f"✅ Created {len(chunk_paths)} audio chunks using fallback method")
    return chunk_paths


def transcribe_audio_chunks(chunk_paths):
    """
    Transcribe multiple audio chunks and combine the results.
    Shows detailed progress for each chunk being transcribed.
    """
    transcripts = []
    total_chunks = len(chunk_paths)

    print(f"🎯 Starting transcription of {total_chunks} audio chunks...")

    for i, chunk_path in enumerate(chunk_paths):
        chunk_num = i + 1
        print(f"\n📝 Transcribing chunk {chunk_num}/{total_chunks}: {chunk_path.name}")

        # Show chunk file size
        chunk_size = chunk_path.stat().st_size / (1024 * 1024)
        print(f"   📁 Chunk size: {chunk_size:.1f} MB")

        try:
            # Create a progress bar for this specific chunk
            with tqdm(
                total=100,
                desc=f"Chunk {chunk_num}/{total_chunks}",
                unit="%",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {elapsed}<{remaining}",
            ) as chunk_pbar:

                chunk_pbar.set_description(f"Uploading chunk {chunk_num}")
                chunk_pbar.update(20)

                with open(chunk_path, "rb") as audio_file:
                    chunk_pbar.set_description(f"Processing chunk {chunk_num}")
                    chunk_pbar.update(30)

                    # Note: OpenAI API doesn't provide streaming progress,
                    # so we simulate progress based on typical processing time
                    transcript = openai.audio.transcriptions.create(
                        model="whisper-1", file=audio_file
                    )
                    chunk_pbar.update(50)

                    transcripts.append(transcript.text)
                    chunk_pbar.set_description(f"✅ Chunk {chunk_num} complete")

            print(
                f"   ✅ Chunk {chunk_num} transcribed: {len(transcript.text)} characters"
            )

        except Exception as e:
            print(f"   ❌ Error transcribing chunk {chunk_num}: {e}")
            transcripts.append(f"[Error transcribing chunk {chunk_num}: {str(e)}]")

    # Show overall completion
    successful_chunks = len([t for t in transcripts if not t.startswith("[Error")])
    print(
        f"\n🎉 Transcription complete: {successful_chunks}/{total_chunks} chunks successful"
    )

    # Cleanup chunk files (but keep the original if it was the only chunk)
    if len(chunk_paths) > 1:
        print("🗑️ Cleaning up audio chunks...")
        for chunk_path in chunk_paths:
            try:
                if chunk_path.exists():
                    chunk_path.unlink()
            except PermissionError:
                print(f"⚠️ Could not delete chunk: {chunk_path.name}")

    return "\n\n".join(transcripts)


def transcribe_video(video_path: Path):
    """
    Transcribes the audio from a video file using OpenAI's Whisper API.
    Saves the transcript to a text file in the same directory.
    Handles large files by splitting them into chunks.
    """
    print(f"\n🎬 Starting video processing: {video_path.name}")
    print(f"📁 Video file size: {video_path.stat().st_size / (1024*1024):.1f} MB")

    try:
        # Step 1: Audio extraction with progress
        print("\n🔊 Extracting audio from video...")
        with tqdm(total=100, desc="Loading video", unit="%") as pbar:
            video_clip = VideoFileClip(str(video_path))
            pbar.update(50)

            audio_path = video_path.with_suffix(".mp3")
            print(f"💾 Saving audio to: {audio_path.name}")

            video_clip.audio.write_audiofile(str(audio_path), logger=None)
            pbar.update(50)
            video_clip.close()

        print(f"✅ Audio extracted successfully: {audio_path.name}")
        print(f"📁 Audio file size: {audio_path.stat().st_size / (1024*1024):.1f} MB")

        # Step 2: Split audio if necessary
        chunk_paths = split_audio_with_ffmpeg(audio_path)

        # Step 3: Transcription with progress
        print("\n🗣️ Transcribing audio with Whisper API...")
        transcript_path = video_path.parent / "Meeting Recording_transcript.txt"

        if len(chunk_paths) == 1:
            # Single file transcription
            print(f"🎯 Transcribing single audio file: {chunk_paths[0].name}")
            chunk_size = chunk_paths[0].stat().st_size / (1024 * 1024)
            print(f"📁 Audio file size: {chunk_size:.1f} MB")

            with tqdm(
                total=100,
                desc="Transcribing audio",
                unit="%",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {elapsed}<{remaining}",
            ) as pbar:
                pbar.set_description("Uploading to Whisper API")
                pbar.update(15)

                with open(chunk_paths[0], "rb") as audio_file:
                    pbar.set_description("🔄 Processing with Whisper")
                    pbar.update(25)

                    transcript = openai.audio.transcriptions.create(
                        model="whisper-1", file=audio_file
                    )
                    pbar.update(50)
                    pbar.set_description("✅ Transcription complete")
                    pbar.update(10)

                    transcript_text = transcript.text

            print(f"✅ Transcription complete: {len(transcript_text)} characters")
        else:
            # Multi-chunk transcription
            transcript_text = transcribe_audio_chunks(chunk_paths)

        # Save transcript
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        print(f"✅ Transcript saved: {transcript_path.name}")
        print(f"📄 Transcript length: {len(transcript_text)} characters")

        # Cleanup main audio file
        print(f"🗑️ Cleaning up temporary audio file...")
        try:
            if audio_path.exists():
                audio_path.unlink()
        except PermissionError:
            print(f"⚠️ Could not delete audio file (still in use): {audio_path.name}")

        return transcript_path

    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        import traceback

        traceback.print_exc()
        # Cleanup audio file if it exists
        audio_path = video_path.with_suffix(".mp3")
        try:
            if audio_path.exists():
                audio_path.unlink()
        except PermissionError:
            print(f"⚠️ Could not delete audio file (still in use): {audio_path.name}")
        return None


def chunk_transcript_for_summarization(
    transcript_text: str, max_chunk_size: int = 6000
) -> List[str]:
    """
    Chunks a long transcript into smaller pieces for GPT-4 processing.
    Tries to break at natural sentence boundaries.
    """
    if len(transcript_text) <= max_chunk_size:
        return [transcript_text]

    chunks = []
    words = transcript_text.split()
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + 1  # +1 for space

        if current_length + word_length > max_chunk_size and current_chunk:
            # Try to end at a sentence boundary
            chunk_text = " ".join(current_chunk)

            # Look for the last sentence ending
            for i in range(len(chunk_text) - 1, -1, -1):
                if chunk_text[i] in ".!?":
                    # Found a sentence end, split here
                    chunks.append(chunk_text[: i + 1])
                    remaining = chunk_text[i + 1 :].strip()
                    if remaining:
                        current_chunk = remaining.split()
                        current_length = len(remaining)
                    else:
                        current_chunk = []
                        current_length = 0
                    break
            else:
                # No sentence boundary found, just split at word boundary
                chunks.append(chunk_text)
                current_chunk = []
                current_length = 0

        current_chunk.append(word)
        current_length += word_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def summarize_transcript_chunk(
    chunk_text: str, chunk_index: int, total_chunks: int
) -> str:
    """
    Summarizes a single chunk of transcript text using GPT-4.
    """
    system_prompt = "You are a helpful assistant. Your task is to summarize a meeting transcript chunk. Focus on identifying key questions and their corresponding answers. Format the output as a clean Q&A list."

    if total_chunks > 1:
        user_prompt = f"Please summarize the following transcript chunk ({chunk_index + 1} of {total_chunks}), extracting the main questions and answers:\n\n---\n\n{chunk_text}"
    else:
        user_prompt = f"Please summarize the following transcript, extracting the main questions and answers:\n\n---\n\n{chunk_text}"

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content


def combine_chunk_summaries(chunk_summaries: List[str]) -> str:
    """
    Combines multiple chunk summaries into a final consolidated summary.
    """
    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    combined_content = "\n\n---CHUNK BREAK---\n\n".join(chunk_summaries)

    system_prompt = "You are a helpful assistant. Your task is to consolidate multiple transcript chunk summaries into one coherent final summary. Remove duplicates, organize related Q&As together, and maintain the Q&A format."

    user_prompt = f"Please consolidate the following chunk summaries into one final comprehensive Q&A summary:\n\n{combined_content}"

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content


def summarize_transcript(transcript_path: Path):
    """
    Uses GPT-4 to summarize the transcript in Q&A format.
    Handles long transcripts by chunking them.
    Saves the summary to a text file in the same directory.
    """
    print(f"\n🤖 Starting GPT-4 summarization...")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    if not transcript_text.strip():
        print("❌ Transcript is empty. Skipping summarization.")
        return

    print(f"📊 Processing {len(transcript_text)} characters of transcript")

    try:
        # Check if transcript needs chunking
        chunks = chunk_transcript_for_summarization(transcript_text)

        if len(chunks) == 1:
            print("📄 Transcript fits in single chunk, processing directly...")
            with tqdm(total=100, desc="Summarizing with GPT-4", unit="%") as pbar:
                pbar.set_description("Preparing prompt")
                pbar.update(10)

                pbar.set_description("Sending to GPT-4")
                pbar.update(20)

                summary_text = summarize_transcript_chunk(chunks[0], 0, 1)
                pbar.update(60)

                pbar.set_description("Saving summary")
                summary_path = transcript_path.parent / "Meeting Recording_summary.txt"

                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(summary_text)
                pbar.update(10)
        else:
            print(f"📚 Transcript requires chunking into {len(chunks)} parts...")
            chunk_summaries = []

            with tqdm(
                total=len(chunks), desc="Processing chunks", unit="chunk"
            ) as pbar:
                for i, chunk in enumerate(chunks):
                    pbar.set_description(f"Summarizing chunk {i+1}/{len(chunks)}")
                    chunk_summary = summarize_transcript_chunk(chunk, i, len(chunks))
                    chunk_summaries.append(chunk_summary)
                    pbar.update(1)

            print("🔗 Combining chunk summaries...")
            with tqdm(total=100, desc="Consolidating summaries", unit="%") as pbar:
                pbar.update(20)
                final_summary = combine_chunk_summaries(chunk_summaries)
                pbar.update(60)

                summary_path = transcript_path.parent / "Meeting Recording_summary.txt"
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(final_summary)
                pbar.update(20)

            summary_text = final_summary

        print(f"✅ Summary saved: {summary_path.name}")
        print(f"📄 Summary length: {len(summary_text)} characters")

    except Exception as e:
        print(f"❌ Error during summarization: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Process video file: extract audio, transcribe, and summarize"
    )
    parser.add_argument(
        "video_path", help="Path to the video file or directory containing video files"
    )
    args = parser.parse_args()

    video_path = Path(args.video_path)

    # If the path is a directory, find the first MP4 file
    if video_path.is_dir():
        mp4_files = list(video_path.glob("*.mp4"))
        if not mp4_files:
            print(f"❌ No MP4 files found in directory: {video_path}")
            return
        video_path = mp4_files[0]
        print(f"🎯 Found video file: {video_path.name}")

    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return

    print("🚀 Video Processing Pipeline Started")
    print("=" * 50)
    start_time = time.time()

    # Step 1: Transcribe video
    transcript_path = transcribe_video(video_path)

    if transcript_path:
        # Step 2: Summarize transcript
        summarize_transcript(transcript_path)

    end_time = time.time()
    total_time = end_time - start_time

    print("\n" + "=" * 50)
    print(f"🎉 Video processing completed!")
    print(
        f"⏱️ Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)"
    )
    print("=" * 50)


if __name__ == "__main__":
    main()
