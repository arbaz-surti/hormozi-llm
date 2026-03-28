"""
Migrate chunks from local chunks.jsonl to Pinecone.

Run this once after Step 3 (clean_and_chunk), and again whenever
you add new transcripts and re-run Step 3.

Usage:
    venv/bin/python migrate_to_pinecone.py

Requires in .env:
    PINECONE_API_KEY
    HUGGINGFACE_API_KEY
"""

import json
import os
import time
import requests
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

load_dotenv()

CHUNKS_FILE = "data/chunks.jsonl"
INDEX_NAME = "hormozi"
HF_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
EMBED_DIM = 384
BATCH_SIZE = 100
DELAY = 0.3


def get_embedding(text: str, api_key: str) -> list[float]:
    for attempt in range(3):
        resp = requests.post(
            HF_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"inputs": text},
            timeout=30,
        )
        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            print(f"  HF error (attempt {attempt+1}): {data['error']}")
            time.sleep(5)
            continue
        return data[0] if isinstance(data[0], list) else data
    raise ValueError("Failed to embed after 3 attempts")


def main():
    pinecone_key = os.getenv("PINECONE_API_KEY")
    hf_key = os.getenv("HUGGINGFACE_API_KEY")

    if not pinecone_key:
        raise ValueError("PINECONE_API_KEY not set in .env")
    if not hf_key:
        raise ValueError("HUGGINGFACE_API_KEY not set in .env")

    pc = Pinecone(api_key=pinecone_key)

    # Create index if it doesn't exist
    existing = [i.name for i in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"Creating Pinecone index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        time.sleep(5)
        print("Index created.")
    else:
        print(f"Index '{INDEX_NAME}' already exists.")

    index = pc.Index(INDEX_NAME)

    # Load chunks
    with open(CHUNKS_FILE) as f:
        chunks = [json.loads(line) for line in f]
    print(f"Total chunks in file: {len(chunks)}")

    # Find which chunks are already uploaded
    existing_ids = set()
    try:
        stats = index.describe_index_stats()
        if stats.total_vector_count > 0:
            # Fetch existing IDs in batches
            all_ids = [c["chunk_id"] for c in chunks]
            for i in range(0, len(all_ids), 1000):
                batch_ids = all_ids[i:i+1000]
                result = index.fetch(ids=batch_ids)
                existing_ids.update(result.vectors.keys())
    except Exception:
        pass

    new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
    print(f"Already in Pinecone: {len(existing_ids)}")
    print(f"New chunks to upload: {len(new_chunks)}")

    if not new_chunks:
        print("Nothing to do — all chunks already in Pinecone.")
        return

    # Embed and upsert
    vectors = []
    for chunk in tqdm(new_chunks, desc="Embedding & uploading"):
        embedding = get_embedding(chunk["text"], hf_key)
        vectors.append({
            "id": chunk["chunk_id"],
            "values": embedding,
            "metadata": {
                "text": chunk["text"][:2000],  # Pinecone metadata limit
                "title": chunk["title"],
                "video_id": chunk["video_id"],
                "source_url": chunk["source_url"],
                "channel": chunk["channel"],
            },
        })

        if len(vectors) >= BATCH_SIZE:
            index.upsert(vectors=vectors)
            vectors = []
            time.sleep(DELAY)

    if vectors:
        index.upsert(vectors=vectors)

    total = index.describe_index_stats().total_vector_count
    print(f"\nDone. Total vectors in Pinecone: {total}")


if __name__ == "__main__":
    main()
