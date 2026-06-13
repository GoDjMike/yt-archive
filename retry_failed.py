#!/usr/bin/env python3
"""
Retry any incomplete downloads from targets.md.

Thin wrapper around `download_audio.py` that adds a confirmation prompt
listing the first few URLs, so you don't accidentally kick off a multi-hour
session after a crash.
"""

import sys
from pathlib import Path

from download_audio import main as download_main, parse_targets_file


def main():
 base_dir = Path(__file__).parent
 targets_file = base_dir / "targets.md"

 targets = parse_targets_file(targets_file)
 incomplete = [t for t in targets if not t["complete"]]

 if not incomplete:
 print("No failed downloads to retry!")
 return

 print(f"Found {len(incomplete)} incomplete videos to retry")

 print("\nFirst 5 incomplete videos:")
 for i, target in enumerate(incomplete[:5]):
 print(f" {i + 1}. {target['url']}")

 proceed = input(
 f"\nRetry downloading {len(incomplete)} failed videos? (y/n): "
 )
 if proceed.lower() != "y":
 print("Cancelled")
 return

 # download_audio.main() only processes incomplete entries, so this is
 # the actual retry.
 download_main()


if __name__ == "__main__":
 main()
