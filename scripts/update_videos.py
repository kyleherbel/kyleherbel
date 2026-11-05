#!/usr/bin/env python3
"""Rewrite the Latest videos block in README.md from the YouTube channel page."""
import json
import pathlib
import re
import sys
import urllib.request

CHANNEL_VIDEOS = "https://www.youtube.com/@kyleherbel/videos"
README = pathlib.Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- VIDEOS:START -->", "<!-- VIDEOS:END -->"
COUNT = 5


def fetch_page():
    request = urllib.request.Request(
        CHANNEL_VIDEOS,
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def find_videos(node, found):
    if isinstance(node, dict):
        lockup = node.get("lockupViewModel")
        if lockup and "VIDEO" in lockup.get("contentType", ""):
            title = (
                lockup.get("metadata", {})
                .get("lockupMetadataViewModel", {})
                .get("title", {})
                .get("content")
            )
            if title and lockup.get("contentId"):
                found.append((lockup["contentId"], title))
        renderer = node.get("videoRenderer")
        if renderer:
            found.append((renderer["videoId"], renderer["title"]["runs"][0]["text"]))
        for value in node.values():
            find_videos(value, found)
    elif isinstance(node, list):
        for value in node:
            find_videos(value, found)


def latest_videos(page):
    match = re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S)
    if not match:
        return []
    found = []
    find_videos(json.loads(match.group(1)), found)
    unique = list(dict.fromkeys(found))
    return unique[:COUNT]


def main():
    try:
        videos = latest_videos(fetch_page())
    except Exception as error:  # A blocked request must not wipe the list.
        print(f"::warning::Could not read YouTube: {error}")
        return 0
    if not videos:
        print("::warning::No videos found on the channel page; README left as is.")
        return 0
    lines = [
        f"- [{title.replace('[', '(').replace(']', ')')}](https://www.youtube.com/watch?v={video_id})"
        for video_id, title in videos
    ]
    text = README.read_text(encoding="utf-8")
    block = "\n".join([START, *lines, END])
    updated, replaced = re.subn(
        re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S
    )
    if not replaced:
        print("::error::Markers not found in README.md")
        return 1
    README.write_text(updated, encoding="utf-8")
    print(f"Wrote {len(lines)} videos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
