#!/usr/bin/env python3
"""
yt-archivist: Download audio from a list of YouTube URLs and organize it
into per-series subfolders, tracking completion in a markdown manifest.

State is read from and written back to a `targets.md` file. Each entry is
one URL plus its current status. The `series` field controls the output
subfolder; the `filepath` field records where the audio landed.

Designed for long-form content (3-15 hour videos): download is single-attempt
with duration verification, and the manifest makes interrupted runs resumable.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# --- Configuration (tweak to taste) ---

# Audio format for ffmpeg conversion. Opus is a good default: small files,
# high quality. Switch to mp3, m4a, aac, wav if your player needs them.
AUDIO_FORMAT = "opus"

# ffmpeg audio quality for the chosen format. 0 = best, 10 = worst.
# See `man ffmpeg` for codec-specific ranges.
AUDIO_QUALITY = "0"

# If the downloaded file's duration differs from the source video by more
# than this percentage, treat the download as suspicious and fail it.
DURATION_TOLERANCE_PERCENT = 5.0

# Fallback series name when an entry has no `series:` field and no filepath
# from which to infer one. Almost always you'll want to specify explicitly.
UNCATEGORIZED = "Uncategorized"


def get_audio_duration(filepath):
 """Get duration of an audio file in seconds via ffprobe, or None on failure."""
 try:
 result = subprocess.run(
 [
 "ffprobe",
 "-v",
 "quiet",
 "-print_format",
 "json",
 "-show_format",
 filepath,
 ],
 capture_output=True,
 text=True,
 check=True,
 )
 info = json.loads(result.stdout)
 return float(info["format"]["duration"])
 except Exception:
 return None


def get_video_info(url):
 """Get video title and duration via yt-dlp, or None on failure."""
 try:
 result = subprocess.run(
 ["yt-dlp", "--dump-json", "--no-download", "--no-playlist", url],
 capture_output=True,
 text=True,
 check=True,
 )
 # yt-dlp can emit multiple JSON objects (e.g. subtitles). Take the first valid one.
 for line in result.stdout.strip().split("\n"):
 if not line.strip():
 continue
 try:
 info = json.loads(line)
 except json.JSONDecodeError:
 continue
 return {
 "title": info.get("title", "Unknown"),
 "duration": info.get("duration", 0),
 "id": info.get("id", ""),
 }
 return None
 except subprocess.CalledProcessError as e:
 print(f"Error getting video info for {url}: yt-dlp exited {e.returncode}")
 if e.stderr:
 print(f" stderr: {e.stderr.strip()}")
 return None
 except Exception as e:
 print(f"Error getting video info for {url}: {e}")
 return None


def sanitize_filename(title):
 """Turn a video title into a filesystem-safe filename stem."""
 # Strip characters that are illegal in filenames on common platforms.
 sanitized = re.sub(r'[<>:"/\\|?*]', "", title)
 # Collapse whitespace, dashes, and brackets into single underscores.
 sanitized = re.sub(r"[\s\-\[\](){}]+", "_", sanitized)
 # Squeeze runs of underscores and trim the edges.
 sanitized = re.sub(r"_+", "_", sanitized).strip("_")
 return sanitized


def infer_series_from_filepath(filepath):
 """Pull a series name out of an existing filepath for backward compat.

 e.g. `files/Star-Wars-X-Wing/foo.opus` -> `Star-Wars-X-Wing`.
 Returns UNCATEGORIZED if the path doesn't have a parent directory.
 """
 if not filepath:
 return UNCATEGORIZED
 parts = Path(filepath).parts
 # Walk back from the end to find the first directory component that
 # isn't `files` (the project root convention).
 for part in reversed(parts[:-1]):
 if part and part != "files":
 return part
 return UNCATEGORIZED


def parse_targets_file(targets_path):
 """Parse a targets.md file into a list of dicts.

 Recognized per-entry fields (one URL line followed by indented fields):
 [] <url> (required, must be the first line of an entry)
 - series: <name> (optional; falls back to filepath inference)
 - filepath: <path> (optional; set after successful download)
 - complete: true|true/false (required; "true/false" means not done)

 Returns a list of dicts: {url, series, filepath, complete, line_number}.
 """
 with open(targets_path, "r") as f:
 lines = f.readlines()

 entries = []
 i = 0
 while i < len(lines):
 stripped = lines[i].strip()
 # Entry header: a markdown-style checkbox followed by a URL.
 if stripped.startswith("[] ") and "://" in stripped:
 url = stripped[3:].strip()
 entry = {
 "url": url,
 "series": "",
 "filepath": "",
 "complete": False,
 "line_number": i + 1, # 1-indexed for error messages
 }

 # Look at the next few lines for the entry's status fields.
 for j in range(i + 1, min(i + 4, len(lines))):
 field_line = lines[j].strip()
 # Strip the optional "- " prefix so fields can be either list
 # bullets or plain indented lines.
 if field_line.startswith("- "):
 field_line = field_line[2:].strip()

 if ":" not in field_line:
 continue
 key, _, value = field_line.partition(":")
 key = key.strip().lower()
 value = value.strip()

 if key == "series":
 entry["series"] = value
 elif key == "filepath":
 # Treat "-" or empty as "no file yet".
 if value and value != "-":
 entry["filepath"] = value
 elif key == "complete":
 # "true/false" is the sentinel for "not yet downloaded".
 entry["complete"] = value.lower() == "true"

 entries.append(entry)
 i += 1

 # Backfill series for old-style entries that only have a filepath.
 for entry in entries:
 if not entry["series"]:
 entry["series"] = infer_series_from_filepath(entry["filepath"])

 return entries


def format_targets_entry(url, series, filepath, complete):
 """Render a single entry back to markdown."""
 lines = [f"[] {url}"]
 if series:
 lines.append(f" - series: {series}")
 if filepath:
 lines.append(f" - filepath: {filepath}")
 lines.append(f" - complete: {'true' if complete else 'true/false'}")
 return "\n".join(lines)


def update_targets_file(targets_path, url, filepath, series, complete=True):
 """Rewrite a single entry in targets.md with the new status."""
 with open(targets_path, "r") as f:
 content = f.read()

 lines = content.split("\n")
 for i, line in enumerate(lines):
 stripped = line.strip()
 if not (stripped.startswith("[] ") and url in stripped):
 continue
 # Find the end of this entry: the next `[]` URL line, or EOF.
 end = i + 1
 while end < len(lines) and not lines[end].strip().startswith("[] "):
 end += 1
 new_block = format_targets_entry(url, series, filepath, complete)
 lines[i:end] = new_block.split("\n")
 break

 with open(targets_path, "w") as f:
 f.write("\n".join(lines))


def download_audio(url, series, files_dir):
 """Download audio for a single URL into the given series subfolder.

 Returns (success: bool, message: str). On success, `message` is the
 relative filepath of the downloaded file.
 """
 try:
 print(f"\n{'=' * 60}")
 print(f"GETTING VIDEO INFO FOR: {url}")
 print(f"{'=' * 60}")

 info = get_video_info(url)
 if not info:
 return False, "Could not get video info"

 title = info["title"]
 duration = info["duration"]
 duration_hours = duration / 3600 if duration else 0

 print(f"VIDEO TITLE: {title}")
 print(f"DURATION: {duration_hours:.1f} hours ({duration} seconds)")

 if not series:
 return False, (
 f"No series specified for URL and cannot infer one. "
 f"Add `series: <name>` to the entry in targets.md."
 )

 full_output_dir = os.path.join(files_dir, series)
 os.makedirs(full_output_dir, exist_ok=True)
 print(f"SERIES FOLDER: {series}")

 safe_title = sanitize_filename(title)
 output_template = os.path.join(full_output_dir, f"{safe_title}.%(ext)s")
 print(f"OUTPUT FILE: {safe_title}.{AUDIO_FORMAT}")
 print("STARTING DOWNLOAD...")
 print("=" * 60)

 cmd = [
 "yt-dlp",
 "--extract-audio",
 "--audio-format",
 AUDIO_FORMAT,
 "--audio-quality",
 AUDIO_QUALITY,
 "--output",
 output_template,
 "--no-playlist",
 "--progress",
 "--newline",
 url,
 ]

 process = subprocess.Popen(
 cmd,
 stdout=subprocess.PIPE,
 stderr=subprocess.STDOUT,
 text=True,
 bufsize=1,
 universal_newlines=True,
 )
 for line in process.stdout:
 print(line.rstrip())
 process.wait()

 if process.returncode != 0:
 print(f"\n{'=' * 60}")
 print("DOWNLOAD FAILED!")
 print("=" * 60)
 return False, f"yt-dlp failed with exit code {process.returncode}"

 print(f"\n{'=' * 60}")
 print("DOWNLOAD COMPLETED SUCCESSFULLY!")
 print("=" * 60)

 # Locate the actual file yt-dlp produced.
 expected = os.path.join(full_output_dir, f"{safe_title}.{AUDIO_FORMAT}")
 if os.path.exists(expected):
 downloaded_file = expected
 else:
 # Fall back to a fuzzy search in case the extension is unexpected.
 downloaded_file = None
 for candidate in os.listdir(full_output_dir):
 if (
 safe_title in candidate
 and candidate.endswith((".opus", ".mp3", ".m4a", ".aac", ".wav"))
 ):
 downloaded_file = os.path.join(full_output_dir, candidate)
 break

 if not downloaded_file:
 return False, "Download completed but audio file not found"

 # Sanity check: does the file's duration roughly match the source?
 if duration:
 downloaded_duration = get_audio_duration(downloaded_file)
 if downloaded_duration:
 diff = abs(downloaded_duration - duration)
 diff_pct = (diff / duration) * 100 if duration > 0 else 0
 print("DURATION CHECK:")
 print(f" Original: {duration:.0f}s ({duration / 3600:.1f}h)")
 print(
 f" Downloaded: {downloaded_duration:.0f}s "
 f"({downloaded_duration / 3600:.1f}h)"
 )
 print(f" Difference: {diff:.0f}s ({diff_pct:.1f}%)")
 if diff_pct > DURATION_TOLERANCE_PERCENT:
 print(
 f" ⚠ WARNING: Duration mismatch exceeds "
 f"{DURATION_TOLERANCE_PERCENT}%!"
 )
 return False, f"Duration mismatch: {diff_pct:.1f}% difference"
 print(" ✓ Duration check passed")

 # Store the path relative to the project root so the manifest is
 # portable across machines.
 rel_path = os.path.relpath(downloaded_file, Path(files_dir).parent)
 return True, rel_path

 except Exception as e:
 return False, f"Exception: {e}"


def parse_args():
 parser = argparse.ArgumentParser(
 description="Download audio for each entry in a targets.md manifest."
 )
 parser.add_argument(
 "--targets",
 default="targets.md",
 help="Path to the targets.md manifest (default: targets.md)",
 )
 parser.add_argument(
 "--files-dir",
 default="files",
 help="Directory under which series subfolders are created (default: files)",
 )
 return parser.parse_args()


def main():
 args = parse_args()
 base_dir = Path(__file__).parent
 targets_path = base_dir / args.targets
 files_dir = base_dir / args.files_dir

 if not targets_path.exists():
 print(f"ERROR: targets file not found: {targets_path}")
 sys.exit(1)

 targets = parse_targets_file(targets_path)
 incomplete = [t for t in targets if not t["complete"]]

 print(f"Found {len(targets)} total videos, {len(incomplete)} incomplete")

 if not incomplete:
 print("All videos already downloaded!")
 return

 for i, target in enumerate(incomplete, 1):
 url = target["url"]
 series = target["series"]
 print(f"\n[{i}/{len(incomplete)}] Processing: {url}")

 try:
 success, result = download_audio(url, series, str(files_dir))
 except KeyboardInterrupt:
 print("\nDownload interrupted by user")
 break
 except Exception as e:
 print(f"✗ Unexpected error: {e}")
 continue

 if success:
 print(f"✓ Downloaded to: {result}")
 update_targets_file(targets_path, url, result, series, complete=True)
 else:
 print(f"✗ Failed: {result}")


if __name__ == "__main__":
 main()
