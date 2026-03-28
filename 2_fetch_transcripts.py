"""
Step 2: Fetch transcripts for all videos using youtube-transcript-api.

Usage:
    python3 2_fetch_transcripts.py

Input:
    data/video_ids.json

Output:
    data/transcripts/  — one JSON file per video
    data/failed_ids.json  — videos where transcript fetch failed

No API key needed. Rate limiting is handled automatically.
"""

import json
import os
import time
from pathlib import Path
from tqdm import tqdm
import requests
from http.cookiejar import MozillaCookieJar
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

INPUT_FILE = "data/video_ids.json"
OUTPUT_DIR = "data/transcripts"
FAILED_FILE = "data/failed_ids.json"
COOKIES_FILE = "data/www.youtube.com_cookies.txt"
DELAY_BETWEEN_REQUESTS = 3.0  # seconds — increased to avoid YouTube IP blocks


def fetch_transcript(api, video_id):
    """Fetch transcript, preferring English in any form."""
    transcript_list = api.list(video_id)
    transcripts = list(transcript_list)

    # Find best English transcript: manual > auto-generated
    english = [t for t in transcripts if t.language_code.startswith("en")]
    manual = [t for t in english if not t.is_generated]
    auto = [t for t in english if t.is_generated]

    if manual:
        return manual[0].fetch(), "manual"
    if auto:
        return auto[0].fetch(), "auto"

    # Last resort: translate first available to English
    if transcripts:
        try:
            return transcripts[0].translate("en").fetch(), "translated"
        except Exception:
            pass

    return None, None


def merge_transcript_text(transcript_data):
    """Join transcript segments into a single string."""
    return " ".join(
        seg.text.strip()
        for seg in transcript_data
        if seg.text.strip()
    )


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE) as f:
        videos = json.load(f)

    already_done = {p.stem for p in Path(OUTPUT_DIR).glob("*.json")}
    to_process = [v for v in videos if v["video_id"] not in already_done]

    print(f"Total videos: {len(videos)}")
    print(f"Already fetched: {len(already_done)}")
    print(f"To fetch: {len(to_process)}")

    session = requests.Session()
    jar = MozillaCookieJar(COOKIES_FILE)
    jar.load(ignore_discard=True, ignore_expires=True)
    session.cookies = jar
    api = YouTubeTranscriptApi(http_client=session)
    failed = []

    for video in tqdm(to_process, desc="Fetching transcripts"):
        video_id = video["video_id"]
        try:
            transcript_data, source = fetch_transcript(api, video_id)

            if transcript_data is None:
                failed.append({**video, "reason": "no_transcript"})
                continue

            full_text = merge_transcript_text(transcript_data)
            if len(full_text.strip()) < 100:
                failed.append({**video, "reason": "transcript_too_short"})
                continue

            output = {
                "video_id": video_id,
                "title": video["title"],
                "channel": video["channel"],
                "published_at": video["published_at"],
                "transcript_source": source,
                "transcript": full_text,
                "segments": [
                    {"start": seg.start, "duration": seg.duration, "text": seg.text}
                    for seg in transcript_data
                ],
            }

            with open(f"{OUTPUT_DIR}/{video_id}.json", "w") as f:
                json.dump(output, f, indent=2)

        except (NoTranscriptFound, TranscriptsDisabled):
            failed.append({**video, "reason": "transcripts_disabled"})
        except Exception as e:
            failed.append({**video, "reason": str(e)})

        time.sleep(DELAY_BETWEEN_REQUESTS)

    with open(FAILED_FILE, "w") as f:
        json.dump(failed, f, indent=2)

    success = len(to_process) - len(failed)
    print(f"\nDone. Fetched: {success} | Failed: {len(failed)}")
    print(f"Failed list saved to: {FAILED_FILE}")


if __name__ == "__main__":
    main()
