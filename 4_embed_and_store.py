"""
Step 4: Embed chunks using Ollama and store in a local Chroma vector database.

Usage:
    python3 4_embed_and_store.py

Input:
    data/chunks.jsonl

Output:
    data/chroma/  — local vector database

This is incremental — safe to re-run after fetching more transcripts.
It only embeds chunks not already in the database.
"""

import json
import os
from tqdm import tqdm
import chromadb
import ollama

CHUNKS_FILE = "data/chunks.jsonl"
CHROMA_DIR = "data/chroma"
COLLECTION_NAME = "hormozi"
EMBED_MODEL = "nomic-embed-text"
BATCH_SIZE = 50


def load_chunks():
    with open(CHUNKS_FILE) as f:
        return [json.loads(line) for line in f]


def main():
    os.makedirs(CHROMA_DIR, exist_ok=True)

    # Load chunks
    chunks = load_chunks()
    print(f"Total chunks in file: {len(chunks)}")

    # Connect to Chroma
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Find chunks not yet embedded
    existing_ids = set(collection.get()["ids"])
    new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
    print(f"Already embedded: {len(existing_ids)}")
    print(f"New chunks to embed: {len(new_chunks)}")

    if not new_chunks:
        print("Nothing to do — all chunks already embedded.")
        return

    # Embed and store in batches
    for i in tqdm(range(0, len(new_chunks), BATCH_SIZE), desc="Embedding"):
        batch = new_chunks[i:i + BATCH_SIZE]

        ids = [c["chunk_id"] for c in batch]
        texts = [c["text"] for c in batch]
        metadatas = [
            {
                "video_id": c["video_id"],
                "title": c["title"],
                "channel": c["channel"],
                "published_at": c["published_at"],
                "source_url": c["source_url"],
                "chunk_index": c["chunk_index"],
            }
            for c in batch
        ]

        # Get embeddings from Ollama
        embeddings = []
        for text in texts:
            response = ollama.embed(model=EMBED_MODEL, input=text)
            embeddings.append(response["embeddings"][0])

        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    total = collection.count()
    print(f"\nDone. Total chunks in database: {total}")


if __name__ == "__main__":
    main()
