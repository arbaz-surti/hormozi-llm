# Hormozi LLM — Data Pipeline

## Steps

### Step 1: Get a YouTube API Key
1. Go to https://console.cloud.google.com/
2. Create a project → Enable **YouTube Data API v3**
3. Create credentials → API Key

### Step 2: Fetch Video IDs
```bash
python3 1_fetch_video_ids.py --api-key YOUR_API_KEY
```
Output: `data/video_ids.json`

### Step 3: Fetch Transcripts
```bash
python3 2_fetch_transcripts.py
```
Output: `data/transcripts/*.json` (one per video)
Note: Can be re-run — skips already-fetched videos.

### Step 4: Clean & Chunk
```bash
python3 3_clean_and_chunk.py
```
Output: `data/chunks.jsonl` — ready for embedding

## Next Steps (after this pipeline)
- Embed chunks using OpenAI or a local model
- Store in a vector database (Pinecone, Supabase, Chroma)
- Build a RAG query interface
