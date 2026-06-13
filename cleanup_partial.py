#!/usr/bin/env python3
"""
yt-archivist: Cleanup utility.

Scans the files directory for partial or failed downloads and offers to
delete them and reset their corresponding entries in the manifest so the
main download script will retry them.

What counts as "partial":
 - Video files (webm, mp4, mkv, avi, mov) that yt-dlp couldn't convert.
 - Audio files smaller than `MIN_AUDIO_SIZE_MB` — almost always truncated
 downloads of long-form content.

By default this runs in dry-run mode and only prints what it would do.
Pass --no-dry-run to actually delete and reset.
"""

import argparse
import os
import sys
from pathlib import Path

# Reuse the manifest parser and writer from the main script.
from download_audio import parse_targets_file, update_targets_file

# --- Configuration ---

# Audio files smaller than this are treated as suspicious. The threshold
# assumes long-form content (audiobooks, lectures); for short clips you may
# need to lower it.
MIN_AUDIO_SIZE_MB = 50

# Video container extensions left over when ffmpeg conversion fails.
# These are always safe to delete — they're not the final artifact.
VIDEO_EXTENSIONS = (".webm", ".mp4", ".mkv", ".avi", ".mov")

# Audio extensions the downloader can produce. Used for the "suspiciously
# small" check and the folder-status summary.
AUDIO_EXTENSIONS = (".opus", ".mp3", ".m4a", ".aac", ".wav")


def find_problematic_files(files_dir, min_audio_mb):
 """Walk files_dir and return a list of {path, type, reason, should_reset_target}."""
 issues = []
 min_bytes = min_audio_mb * 1024 * 1024

 for root, _dirs, files in os.walk(files_dir):
 for name in files:
 filepath = os.path.join(root, name)
 lower = name.lower()

 if lower.endswith(VIDEO_EXTENSIONS):
 issues.append(
 {
 "path": filepath,
 "type": "unconverted_video",
 "reason": "Video container left behind by failed ffmpeg conversion",
 "should_reset_target": True,
 }
 )
 elif lower.endswith(AUDIO_EXTENSIONS):
 size = os.path.getsize(filepath)
 if size < min_bytes:
 size_mb = size / (1024 * 1024)
 issues.append(
 {
 "path": filepath,
 "type": "suspicious_small",
 "reason": f"Audio file unusually small ({size_mb:.1f}MB)",
 "should_reset_target": True,
 }
 )
 return issues


def show_folder_status(files_dir):
 """Print a per-subfolder summary of completed vs other files."""
 print("FOLDER STATUS:")
 print("=" * 60)

 for entry in sorted(os.listdir(files_dir)):
 sub = os.path.join(files_dir, entry)
 if not os.path.isdir(sub):
 continue
 names = os.listdir(sub)
 audio = [n for n in names if n.lower().endswith(AUDIO_EXTENSIONS)]
 other = [n for n in names if not n.lower().endswith(AUDIO_EXTENSIONS)]
 print(f"{entry}:")
 print(f" .audio files: {len(audio)}")
 if other:
 exts = sorted({n.rsplit(".", 1)[-1] for n in other})
 print(f" ⚠ other files: {len(other)} ({', '.join(exts)})")
 print()


def find_target_url_for_file(targets, filename):
 """Return the URL whose recorded filepath matches this file, or None."""
 for target in targets:
 fp = target.get("filepath", "")
 if fp and filename in fp:
 return target["url"]
 return None


def parse_args():
 parser = argparse.ArgumentParser(
 description="Find and (optionally) delete partial downloads."
 )
 parser.add_argument(
 "--targets",
 default="targets.md",
 help="Path to the targets.md manifest (default: targets.md)",
 )
 parser.add_argument(
 "--files-dir",
 default="files",
 help="Directory containing series subfolders (default: files)",
 )
 parser.add_argument(
 "--threshold-mb",
 type=float,
 default=MIN_AUDIO_SIZE_MB,
 help=f"Min size for a 'complete' audio file, in MB (default: {MIN_AUDIO_SIZE_MB})",
 )
 parser.add_argument(
 "--dry-run",
 action="store_true",
 default=True,
 help="Print what would happen without deleting or modifying anything (default)",
 )
 parser.add_argument(
 "--no-dry-run",
 dest="dry_run",
 action="store_false",
 help="Actually delete files and reset their manifest entries",
 )
 return parser.parse_args()


def main():
 args = parse_args()
 base_dir = Path(__file__).parent
 files_dir = base_dir / args.files_dir
 targets_path = base_dir / args.targets

 if not files_dir.exists():
 print(f"ERROR: files directory not found: {files_dir}")
 sys.exit(1)

 print("yt-archivist cleanup")
 print("=" * 60)
 if args.dry_run:
 print("(DRY RUN — no files will be deleted, manifest will not be changed)")
 print("=" * 60)

 show_folder_status(files_dir)

 issues = find_problematic_files(files_dir, args.threshold_mb)

 if not issues:
 print("No partial or problematic files found!")
 return

 print(f"FOUND {len(issues)} PROBLEMATIC FILES:")
 print("=" * 60)

 targets = parse_targets_file(targets_path) if targets_path.exists() else []
 urls_to_reset = set()

 for i, info in enumerate(issues, 1):
 rel = os.path.relpath(info["path"], files_dir)
 filename = os.path.basename(info["path"])
 print(f"{i:2d}. {rel}")
 print(f" Type: {info['type']}")
 print(f" Reason: {info['reason']}")
 if info.get("should_reset_target"):
 url = find_target_url_for_file(targets, filename)
 if url:
 urls_to_reset.add(url)
 print(f" → Would reset target: {url[:60]}...")
 print()

 print(f"Would delete {len(issues)} files, reset {len(urls_to_reset)} targets.")

 if args.dry_run:
 print("Pass --no-dry-run to actually perform the cleanup.")
 return

 if not sys.stdin.isatty():
 # Non-interactive (e.g. piped from cron) — require an explicit env opt-in.
 if os.environ.get("YT_ARCHIVIST_CLEANUP_CONFIRM") != "yes":
 print("Refusing to delete in non-interactive mode without confirmation.")
 print("Set YT_ARCHIVIST_CLEANUP_CONFIRM=yes to override.")
 sys.exit(2)
 proceed = "y"
 else:
 proceed = input("Proceed? (y/n): ")

 if proceed.lower() != "y":
 print("Cleanup cancelled")
 return

 deleted = 0
 for info in issues:
 try:
 os.remove(info["path"])
 print(f"✓ Deleted: {os.path.relpath(info['path'], files_dir)}")
 deleted += 1
 except Exception as e:
 print(f"✗ Failed to delete {info['path']}: {e}")

 # Build a quick url->series lookup so the reset preserves the series.
 target_series = {t["url"]: t["series"] for t in targets}

 reset = 0
 for url in urls_to_reset:
 try:
 # Blank the filepath and mark incomplete, but keep the series so
 # the next download attempt routes to the same subfolder.
 update_targets_file(
 targets_path,
 url,
 filepath="",
 series=target_series.get(url, ""),
 complete=False,
 )
 print(f"✓ Reset target: {url[:60]}...")
 reset += 1
 except Exception as e:
 print(f"✗ Failed to reset target {url}: {e}")

 print(f"\nDeleted {deleted}/{len(issues)} files.")
 print(f"Reset {reset}/{len(urls_to_reset)} targets.")
 print("Re-run download_audio.py to retry the failed downloads.")


if __name__ == "__main__":
 main()
