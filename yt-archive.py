#!/usr/bin/env python3
"""
Convenience entrypoint for yt-archivist.

This script keeps setup simple and cross-platform:
- ensure a uv virtualenv exists
- install yt-dlp dependency
- optionally collect new YouTube URLs into targets.md
- run the main downloader

Run:
    python3 yt-archive.py

Then add URLs and run downloads with flags like --audio-format mp3.
"""

import argparse
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_command(cmd, **kwargs):
    """Run a command from the repository root and return CompletedProcess."""
    print("+", " ".join(shlex.quote(str(part)) for part in cmd))
    return subprocess.run(cmd, cwd=ROOT, check=True, **kwargs)


def ensure_environment():
    """
    Make sure uv + .venv + deps are available.
    """
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("Missing required tool: uv. Install uv, then retry.")

    venv = ROOT / ".venv"
    if not venv.exists():
        run_command([uv, "venv"])

    requirements = ROOT / "requirements.txt"
    if requirements.exists():
        run_command([uv, "pip", "install", "-r", str(requirements)])

    return uv


def collect_targets(targets_path: Path, series: str):
    """
    Read YouTube URLs from stdin and append them as new manifest entries.
    """
    print("Paste YouTube URLs, one per line.")
    print("Press Enter on an empty line when done.")

    entries = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        if "://" not in line:
            print("  Skipping: looks like a non-URL")
            continue
        if "youtube.com" not in line and "youtu.be" not in line:
            print("  Warning: URL is not a YouTube link; adding anyway.")
        entries.append(line)

    if not entries:
        print("No URLs provided; no changes written.")
        return False

    content = []
    for url in entries:
        content.append(f"[] {url}")
        content.append(f" - series: {series}")
        content.append(" - complete: false")
        content.append("")

    # Keep entries visually separated from existing content.
    if targets_path.exists() and targets_path.stat().st_size > 0:
        with targets_path.open("rb") as f:
            existing = f.read()
        if existing and not existing.endswith(b"\n"):
            target_contents = "\n" + "\n".join(content).rstrip() + "\n"
        else:
            target_contents = "\n".join(content).rstrip() + "\n"
    else:
        target_contents = "\n".join(content).rstrip() + "\n"

    if not target_contents.endswith("\n"):
        target_contents += "\n"

    # Append in text mode to avoid platform-specific newline surprises.
    with targets_path.open("a", encoding="utf-8") as f:
        f.write(target_contents)

    print(f"Added {len(entries)} URL(s) to {targets_path}")
    return True


def run_downloader(args):
    """Ensure env and invoke download_audio.py."""
    ensure_environment()
    targets = str(Path(args.targets))
    if not Path(targets).is_absolute():
        targets = str(ROOT / targets)
    files_dir = str(Path(args.files_dir))
    if not Path(files_dir).is_absolute():
        files_dir = str(ROOT / files_dir)

    cmd = [
        "uv",
        "run",
        "python",
        "download_audio.py",
        "--targets",
        targets,
        "--files-dir",
        files_dir,
    ]
    if args.audio_format:
        cmd.extend(["--audio-format", args.audio_format])

    run_command(cmd)


def parse_args():
    parser = argparse.ArgumentParser(
        description="yt-archivist cross-platform runner and entry helper"
    )
    parser.add_argument(
        "--targets",
        default="targets.md",
        help="Path to targets manifest (default: targets.md)",
    )
    parser.add_argument(
        "--files-dir",
        default="files",
        help="Download directory (default: files)",
    )
    parser.add_argument(
        "--audio-format",
        default=None,
        help="Pass through to yt-dlp (e.g. mp3, opus, m4a).",
    )
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Open an interactive URL input prompt and append to targets.md.",
    )
    parser.add_argument(
        "--series",
        default="Uncategorized",
        help="Series name used by --collect (default: Uncategorized).",
    )
    parser.add_argument(
        "--and-run",
        action="store_true",
        help="Run downloader after collecting URLs.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    targets_path = Path(args.targets)
    if not targets_path.is_absolute():
        targets_path = ROOT / targets_path

    if args.collect:
        added = collect_targets(targets_path, args.series)
        if args.and_run and added:
            run_downloader(args)
        elif args.and_run and not added:
            print("--and-run specified but no URLs were added.")
        return

    run_downloader(args)


if __name__ == "__main__":
    main()
