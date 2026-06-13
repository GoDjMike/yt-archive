# targets.example.md
# Template for a yt-archivist manifest.
#
# Copy this to `targets.md` and fill in your own URLs. Each entry is:
#
# [] <youtube-url>
# - series: <subfolder-name> (the downloader puts files in files/<subfolder-name>/)
# - filepath: <relative/path> (written by the tool after a successful download)
# - complete: true|true/false (true/false = pending; true = done)
#
# You can group entries visually with blank lines or `---` separators. The
# parser ignores anything that isn't an entry.

[] https://www.youtube.com/watch?v=VIDEO_ID_1
 - series: My-Series
 - filepath: files/My-Series/SAMPLE_TITLE_1.opus
 - complete: true

[] https://www.youtube.com/watch?v=VIDEO_ID_2
 - series: My-Series
 - filepath:
 - complete: true/false

[] https://www.youtube.com/watch?v=VIDEO_ID_3
 - series: Another-Series
 - filepath:
 - complete: true/false

---
