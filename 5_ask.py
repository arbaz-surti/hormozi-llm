"""
Step 5: Ask a business question and get advice in Alex Hormozi's style.

Usage:
    python3 5_ask.py
    python3 5_ask.py --question "How do I get my first 10 customers?"
"""

import argparse
import chromadb
import ollama

CHROMA_DIR = "data/chroma"
COLLECTION_NAME = "hormozi"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2"
TOP_K = 5  # number of relevant chunks to retrieve


SYSTEM_PROMPT = """You are an AI trained on Alex Hormozi's business content.
Answer questions the way Alex Hormozi would — direct, no fluff, actionable, brutally honest.
Use his frameworks, vocabulary, and mental models when relevant (offers, leads, leverage, etc).
Base your answer strictly on the provided context from his content.
If the context doesn't cover the question well, say so honestly."""


def get_answer(question: str, verbose: bool = False) -> str:
    # Connect to Chroma
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    # Embed the question
    response = ollama.embed(model=EMBED_MODEL, input=question)
    question_embedding = response["embeddings"][0]

    # Retrieve most relevant chunks
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=TOP_K,
        include=["documents", "metadatas"]
    )

    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]

    if verbose:
        print("\n--- Sources retrieved ---")
        for i, (chunk, meta) in enumerate(zip(chunks, metadatas)):
            print(f"[{i+1}] {meta['title']} ({meta['source_url']})")
            print(f"    {chunk[:100]}...")
        print()

    # Build context string
    context = "\n\n---\n\n".join(
        f"From: \"{meta['title']}\"\n{chunk}"
        for chunk, meta in zip(chunks, metadatas)
    )

    # Ask the LLM
    prompt = f"""Here is relevant content from Alex Hormozi's videos:

{context}

---

Question: {question}

Answer as Alex Hormozi would, based on the content above:"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    return response["message"]["content"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default=None)
    parser.add_argument("--verbose", action="store_true", help="Show source chunks")
    args = parser.parse_args()

    if args.question:
        print(f"\nQuestion: {args.question}\n")
        print(get_answer(args.question, verbose=args.verbose))
    else:
        print("Hormozi AI — ask a business question. Type 'quit' to exit.\n")
        while True:
            question = input("You: ").strip()
            if question.lower() in ("quit", "exit", "q"):
                break
            if not question:
                continue
            print("\nHormozi AI:")
            print(get_answer(question))
            print()


if __name__ == "__main__":
    main()
