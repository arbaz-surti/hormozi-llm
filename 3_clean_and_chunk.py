"""
Step 3: Clean transcripts and split into chunks ready for embedding.

Usage:
    python3 3_clean_and_chunk.py

Input:
    data/transcripts/  — raw transcript JSONs

Output:
    data/chunks.jsonl  — one JSON object per line, each a chunk ready for embedding

Chunking strategy:
    - ~500 words per chunk with 50-word overlap
    - Each chunk retains video metadata for attribution
"""

import json
import os
import re
from pathlib import Path

INPUT_DIR = "data/transcripts"
OUTPUT_FILE = "data/chunks.jsonl"

CHUNK_SIZE = 500      # words per chunk
CHUNK_OVERLAP = 50    # words of overlap between chunks


def clean_text(text):
    """Remove transcript artifacts and normalize whitespace."""
    # Remove [Music], [Applause], etc.
    text = re.sub(r"\[.*?\]", "", text)
    # Remove filler sounds
    text = re.sub(r"\b(uh|um|hmm|mhm)\b", "", text, flags=re.IGNORECASE)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += chunk_size - overlap

    return chunks


def main():
    transcript_files = list(Path(INPUT_DIR).glob("*.json"))
    print(f"Processing {len(transcript_files)} transcripts...")

    total_chunks = 0

    with open(OUTPUT_FILE, "w") as out_f:
        for fpath in transcript_files:
            with open(fpath) as f:
                data = json.load(f)

            raw_text = data.get("transcript", "")
            clean = clean_text(raw_text)

            if len(clean.split()) < 50:
                continue  # Skip very short transcripts

            chunks = split_into_chunks(clean)

            for i, chunk_text in enumerate(chunks):
                chunk = {
                    "chunk_id": f"{data['video_id']}_chunk_{i}",
                    "video_id": data["video_id"],
                    "title": data["title"],
                    "channel": data["channel"],
                    "published_at": data["published_at"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "text": chunk_text,
                    "word_count": len(chunk_text.split()),
                    "source_url": f"https://www.youtube.com/watch?v={data['video_id']}",
                }
                out_f.write(json.dumps(chunk) + "\n")
                total_chunks += 1

    print(f"Done. Total chunks: {total_chunks}")
    print(f"Output: {OUTPUT_FILE}")

    # Print a sample
    with open(OUTPUT_FILE) as f:
        sample = json.loads(f.readline())
    print(f"\nSample chunk from: '{sample['title']}'")
    print(f"Text preview: {sample['text'][:200]}...")


if __name__ == "__main__":
    main()
