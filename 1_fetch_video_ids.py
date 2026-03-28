"""
Step 1: Fetch all video IDs from Alex Hormozi's YouTube channels.

Usage:
    python3 1_fetch_video_ids.py

Output:
    data/video_ids.json  — list of {video_id, title, channel, published_at}

Uses the uploads playlist method — gets every video without limits.
"""

import json
import argparse
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

CHANNELS = [
    {"name": "Alex Hormozi", "handle": "AlexHormozi"},
    {"name": "Acquisition.com", "handle": "AcquisitionCom"},
]


def get_uploads_playlist_id(youtube, handle):
    """Get the uploads playlist ID for a channel via its handle."""
    response = youtube.channels().list(
        part="contentDetails,snippet",
        forHandle=handle
    ).execute()

    items = response.get("items", [])
    if not items:
        print(f"  Could not find channel with handle: @{handle}")
        return None, None

    channel_name = items[0]["snippet"]["title"]
    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return uploads_playlist_id, channel_name


def get_all_videos_from_playlist(youtube, playlist_id, channel_name):
    """Iterate through all pages of a playlist to get every video."""
    videos = []
    next_page_token = None
    page = 1

    while True:
        print(f"  Fetching page {page} ({len(videos)} videos so far)...")
        response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in response.get("items", []):
            video_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]
            published_at = item["contentDetails"].get("videoPublishedAt", "")

            # Skip deleted/private videos
            if title in ("Deleted video", "Private video"):
                continue

            videos.append({
                "video_id": video_id,
                "title": title,
                "channel": channel_name,
                "published_at": published_at,
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
        page += 1

    return videos


def safe_get_all_videos(youtube, playlist_id, channel_name):
    try:
        return get_all_videos_from_playlist(youtube, playlist_id, channel_name)
    except HttpError as e:
        print(f"  Error fetching playlist {playlist_id}: {e}")
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=None, help="YouTube Data API v3 key (overrides .env)")
    parser.add_argument("--output", default="data/video_ids.json")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError("Set YOUTUBE_API_KEY in your .env file or pass --api-key")

    os.makedirs("data", exist_ok=True)
    youtube = build("youtube", "v3", developerKey=api_key)

    all_videos = []
    for channel in CHANNELS:
        print(f"\nFetching channel: {channel['name']} (@{channel['handle']})")
        playlist_id, channel_name = get_uploads_playlist_id(youtube, channel["handle"])
        if not playlist_id:
            continue
        print(f"  Found channel: {channel_name}")
        print(f"  Uploads playlist: {playlist_id}")
        videos = safe_get_all_videos(youtube, playlist_id, channel_name)
        print(f"  Total videos: {len(videos)}")
        all_videos.extend(videos)

    # Deduplicate by video_id
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique_videos.append(v)

    with open(args.output, "w") as f:
        json.dump(unique_videos, f, indent=2)

    print(f"\nTotal unique videos across all channels: {len(unique_videos)}")
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
