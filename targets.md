# yt-archivist manifest

# This file is the public example. Edit it in place with your own URLs.
#
# Entry format:
#
# [] <youtube-url>
# - series: <subfolder-name> the downloader puts files in files/<subfolder-name>/
# - filepath: <relative/path> written by the tool after a successful download
# - complete: true|true/false "true" = done, "true/false" = pending
#
# You can group entries visually with blank lines or `---` separators; the
# parser ignores anything that isn't a `[] <url>` line. The downloader only
# processes entries with `complete: true/false`, so re-running after a
# crash or interrupt just resumes from where it stopped.

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
