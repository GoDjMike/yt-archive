# yt-archivist

A small personal tool for batch-downloading the audio of a list of YouTube
videos — typically long-form content like audiobooks, lectures, or
podcasts — and organizing the results into per-series subfolders.

It tracks progress in a markdown manifest (`targets.md`) so interrupted
runs can be resumed safely.

This is **not** an installable library or published package. Clone it,
edit the manifest, run the scripts. That's the whole idea.

## What it does

For each entry in `targets.md`:

1. Looks up the video title and duration with `yt-dlp`.
2. Downloads the audio (default: opus) into `files/<series>/<title>.opus`.
3. Sanity-checks the downloaded duration against the source (flags a
 mismatch > 5% as a failed download).
4. Marks the entry complete in the manifest and records the relative
 filepath.

A second script (`cleanup_partial.py`) sweeps the files directory for
failed conversions and suspiciously small audio files, deletes them, and
resets the corresponding manifest entries so the main downloader will
retry them on the next run.

## Requirements

- macOS, Linux, or Windows 10/11
- Python 3.9+
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) (Python package)
- [`ffmpeg`](https://ffmpeg.org/) / `ffprobe` (CLI tools, for the
 `--extract-audio` conversion and duration checks)

On macOS with Homebrew:

```sh
brew install ffmpeg yt-dlp
```

On Windows:

```powershell
winget install --id Gyan.FFmpeg
uv pip install yt-dlp
```

If `winget` is unavailable, use Chocolatey or Scoop:

```powershell
choco install ffmpeg
```

```powershell
scoop install ffmpeg
```

If `yt-dlp` or `ffprobe` is not on `PATH`, set it explicitly:

```powershell
$env:YT_ARCHIVIST_YT_DLP = "C:\Path\To\yt-dlp.exe"
$env:YT_ARCHIVIST_FFPROBE = "C:\Path\To\ffprobe.exe"
```

## Setup

```sh
git clone <this-repo> ~/dev/projects/yt-archivist
cd ~/dev/projects/yt-archivist

# Create a venv and install the one Python dep
uv venv
uv pip install -r requirements.txt
```

```powershell
git clone <this-repo> C:\Users\<you>\dev\tools\yt-archive
cd C:\Users\<you>\dev\tools\yt-archive

# Create a venv and install the one Python dep
uv venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

## Usage

### 1. Edit the manifest

`targets.md` ships as a 3-entry example. Open it in your editor and
replace the placeholder entries with your own URLs:

```sh
$EDITOR targets.md
```

On Windows PowerShell:

```powershell
notepad targets.md
```

Each entry needs at minimum a URL and a `series` (the subfolder name).
The downloader auto-creates `files/<series>/` on first use.

### 2. Download

```sh
python download_audio.py
```

On Windows:

```powershell
py download_audio.py
```

The script only processes entries marked `complete: true/false`, so it's
safe to re-run after a crash, an interrupt (Ctrl-C), or a network blip.

To target a different manifest or output directory:

```sh
python download_audio.py --targets my-other-list.md --files-dir downloads
```

### 3. Retry, with a confirmation prompt

```sh
python retry_failed.py
```

On Windows:

```powershell
py retry_failed.py
```

Lists the first 5 incomplete URLs, asks for confirmation, then runs the
main downloader. Useful after a long session you don't want to start by
accident.

### 4. Clean up partials

```sh
# See what would happen first
python cleanup_partial.py --dry-run

# Then do it for real
python cleanup_partial.py --no-dry-run
```

On Windows:

```powershell
# See what would happen first
py cleanup_partial.py --dry-run

# Then do it for real
py cleanup_partial.py --no-dry-run
```

Tweak the "suspiciously small" threshold for short-form content:

```sh
python cleanup_partial.py --threshold-mb 5
```

## Manifest format

```
[] https://www.youtube.com/watch?v=VIDEO_ID
 - series: <subfolder-name>
 - filepath: files/<subfolder-name>/<title>.opus
 - complete: true|true/false
```

- `series` is required. It controls the output subfolder.
- `filepath` is written by the tool. You can leave it blank on entries you
 haven't downloaded yet.
- `complete: true/false` is the sentinel for "not yet downloaded". `true`
 means done. The unusual `true/false` form is so the manifest can be
 diffed as plain markdown without a custom "pending" keyword.
- The `[] ` prefix is a markdown checkbox convention — the parser keys
 off it, so keep it on every URL line.
- You can leave blank lines or `---` separators between entries; the
 parser ignores anything that isn't a `[] ` URL line.

## Configuration

The main downloader exposes a few knobs as constants near the top of
`download_audio.py`:

| Constant | Default | What it does |
|----------------------------|---------|-------------------------------------------------|
| `AUDIO_FORMAT` | `opus` | ffmpeg output container |
| `AUDIO_QUALITY` | `0` | ffmpeg quality (`0` = best) |
| `DURATION_TOLERANCE_PERCENT` | `5.0` | % mismatch between source and downloaded audio before failing |
| `UNCATEGORIZED` | `"Uncategorized"` | Fallback series name for entries with no series and no filepath to infer from |

The cleanup script's threshold (`MIN_AUDIO_SIZE_MB = 50`) lives in
`cleanup_partial.py`. For short clips, lower it via `--threshold-mb`.

## Layout

```
.
├── download_audio.py # main downloader
├── retry_failed.py # interactive wrapper around download_audio
├── cleanup_partial.py # sweep + reset for failed downloads
├── targets.md # the manifest — example entries; overwrite with your own URLs
├── files/ # downloaded audio, one subfolder per series
├── requirements.txt # yt-dlp
└── README.md
```

## What's not in git

- `files/` — the actual audio. Large, regenerable, and tied to a
 particular machine's filesystem.
- `.venv/`, `__pycache__/`, `.DS_Store`, `Thumbs.db`, `.claude/` — standard ignores.

## Notes

- Long downloads (3-15 hours per video) are the norm for the use case
 this tool was built for. Network drops happen. The manifest makes
 resume trivial; the cleanup script catches the cases where a
 download "succeeded" but produced a truncated or unconverted file.
- The duration check catches more than just network truncation — it
 also catches yt-dlp's occasional failure to extract the full video.
- `--no-playlist` is always passed to yt-dlp. If you have a playlist
 URL, expand it to individual video URLs first
 (`yt-dlp --flat-playlist -i --print url PLAYLIST_URL`) and paste
 them into the manifest.
