# yt-archivist

A small personal tool for batch-downloading the audio of a list of YouTube
videos and organizing results into per-series subfolders.

It tracks progress in a markdown manifest (`targets.md`) so long runs can be
resumed safely.

This is **not** an installable package. Clone it, add URLs, run the wrapper,
let it handle setup and execution.

## What it does

For each entry in `targets.md`:

1. Looks up title and duration with `yt-dlp`.
2. Downloads audio into `files/<series>/<title>.<ext>`.
3. Checks downloaded duration against source (warns on suspicious mismatch).
4. Marks the entry complete and writes `filepath` in the manifest.

## Requirements

- Windows 10/11, macOS, or Linux
- Python 3.9+
- [uv](https://docs.astral.sh/uv/) (Python environment manager)
- `ffmpeg` / `ffprobe` (for extraction + duration checks)
- `yt-dlp` (installed through `requirements.txt`/`uv`)

Install ffmpeg for your platform:

```sh
# macOS
brew install ffmpeg

# Linux
sudo apt update && sudo apt install -y ffmpeg

# Windows
winget install --id=Gyan.FFmpeg.Git -e
```

Install uv:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows, you can also use the [official installer or winget package](https://github.com/astral-sh/uv).

## Setup

```sh
git clone <this-repo> <dir>
cd <dir>

# One-time bootstrap
uv venv
```

The wrapper will install Python deps automatically on first run.

## Usage

### 1) Add URLs

Fresh entries are:

```md
[] https://youtube.com/watch?v=VIDEO_ID
 - series: MySeries
 - complete: false
```

`filepath` is optional before download; the script writes it after success.

You can add entries manually or via the interactive collector:

```sh
./yt-archive --collect --series MySeries
```

PowerShell:

```powershell
.\yt-archive.bat --collect --series MySeries
```

Then paste URLs one-per-line and submit an empty line to finish.

### 2) Download

From a clean clone:

```sh
# macOS/Linux
./yt-archive

# Windows PowerShell
.\yt-archive.bat
```

Set audio format for the run:

```sh
./yt-archive --audio-format mp3
.\yt-archive.bat --audio-format mp3
```

Use a different manifest/output directory when needed:

```sh
./yt-archive --targets my-targets.md --files-dir downloads
.\yt-archive.bat --targets my-targets.md --files-dir downloads
```

Run add-and-run in one command:

```sh
./yt-archive --collect --and-run --series MySeries --audio-format mp3
.\yt-archive.bat --collect --and-run --series MySeries --audio-format mp3
```

If interrupted, re-run safely:

```sh
./yt-archive
```

Only `complete: false` entries are processed.

### 3) Retry, with a confirmation prompt

```sh
python retry_failed.py
```

### 4) Clean up partials

```sh
python cleanup_partial.py --dry-run
python cleanup_partial.py --no-dry-run
python cleanup_partial.py --threshold-mb 5
```

## Manifest format

```md
[] https://www.youtube.com/watch?v=VIDEO_ID
 - series: <subfolder-name>
 - filepath: files/<subfolder-name>/<title>.<ext>   # optional while planning
 - complete: true|true/false
```

- `series` controls output folder.
- `complete: false` means pending, `true` means complete.
- `filepath` is optional when adding targets; it is filled after successful download.
- Keep the `[] ` prefix on each URL line; the parser uses it to detect entries.
- You can add blank lines or separators between entries.

## Files

- `yt-archive.py` — cross-platform launcher wrapper
- `yt-archive` — macOS/Linux launcher
- `yt-archive.bat` — Windows CMD launcher
- `yt-archive.ps1` — Windows PowerShell launcher
- `download_audio.py` — main downloader
- `retry_failed.py` — optional retry wrapper
- `cleanup_partial.py` — cleanup and reset helper
- `targets.md` — manifest
- `requirements.txt` — Python dependency list
- `files/` — downloaded output (ignored)

## Notes

- Long runs are normal for long-form content.
- `--no-playlist` is always passed to yt-dlp. If you have a playlist URL,
 expand it first with yt-dlp and paste individual video URLs into `targets.md`.
