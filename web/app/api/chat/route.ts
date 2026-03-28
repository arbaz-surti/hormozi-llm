export const runtime = "edge";

import Groq from "groq-sdk";
import { Pinecone } from "@pinecone-database/pinecone";

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
const pc = new Pinecone({ apiKey: process.env.PINECONE_API_KEY! });

const SYSTEM_PROMPT = `You are an AI assistant trained on Alex Hormozi's business content.
Answer questions the way Alex Hormozi would — direct, no fluff, actionable, brutally honest.
Use his frameworks, vocabulary, and mental models (offers, leads, leverage, constraints, etc).
Base your answer strictly on the provided context from his videos.
If the context doesn't cover the topic well, say so honestly rather than making things up.`;

async function getEmbedding(text: string): Promise<number[]> {
  const res = await fetch(
    "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.HUGGINGFACE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ inputs: text, options: { wait_for_model: true } }),
    }
  );
  const data = (await res.json()) as number[] | number[][];
  // nomic-embed-text returns [[...768 floats...]]
  return Array.isArray(data[0]) ? (data as number[][])[0] : (data as number[]);
}

export async function POST(req: Request) {
  const { question } = (await req.json()) as { question: string };

  if (!question?.trim()) {
    return new Response("Missing question", { status: 400 });
  }

  // Embed question + query Pinecone
  const embedding = await getEmbedding(question);
  const index = pc.index(process.env.PINECONE_INDEX_NAME!);
  const results = await index.query({
    vector: embedding,
    topK: 5,
    includeMetadata: true,
  });

  const matches = results.matches ?? [];
  const sources = matches.map((m) => ({
    title: (m.metadata?.title as string) ?? "",
    url: (m.metadata?.source_url as string) ?? "",
  }));

  const context = matches
    .map((m) => `From: "${m.metadata?.title}"\n${m.metadata?.text as string}`)
    .join("\n\n---\n\n");

  // Stream from Groq
  const stream = await groq.chat.completions.create({
    model: "llama-3.1-8b-instant",
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: `Context from Hormozi's videos:\n\n${context}\n\n---\n\nQuestion: ${question}\n\nAnswer as Alex Hormozi would:`,
      },
    ],
    stream: true,
    max_tokens: 1024,
  });

  const encoder = new TextEncoder();
  const readable = new ReadableStream({
    async start(controller) {
      // First line: sources as JSON
      controller.enqueue(encoder.encode(JSON.stringify({ sources }) + "\n"));

      // Then stream the answer
      for await (const chunk of stream) {
        const text = chunk.choices[0]?.delta?.content ?? "";
        if (text) controller.enqueue(encoder.encode(text));
      }
      controller.close();
    },
  });

  return new Response(readable, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
