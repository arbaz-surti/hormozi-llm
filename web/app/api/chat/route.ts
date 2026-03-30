export const runtime = "edge";

import Groq from "groq-sdk";
import { Pinecone } from "@pinecone-database/pinecone";

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
const pc = new Pinecone({ apiKey: process.env.PINECONE_API_KEY! });

const SYSTEM_PROMPT = `You are a business advisor with deep knowledge of Alex Hormozi's frameworks, books, and content.

The person you are advising is building an AI automation agency. Key context:
- Business: B2B AI automation — building custom AI systems and workflows for small and medium businesses
- Stage: Early stage, pre-revenue, validating their first offer
- Goal: Close their first 3 paying clients, then scale to a sustainable monthly revenue

Use this as your baseline. Do not ask them to clarify what their business is — you already know. Only ask clarifying questions about the specific decision they're bringing to you (e.g. who the exact customer is, what they've already tried, what their constraint is).

Your job is to help them think through real business decisions using Hormozi's mental models — things like offer construction, pricing logic, lead generation, constraints, leverage, and unit economics.

Guidelines:
- If critical decision-specific context is missing (e.g. who the exact customer is, what they're selling, what they've tried), ask 1-2 targeted questions before giving advice. Don't ask about their business type — you already know that.
- When you do have enough context, give specific, logical advice grounded in the retrieved content. Reference the actual frameworks (e.g. "The Grand Slam Offer framework says...", "Hormozi's pricing logic is...").
- Do not roleplay as Alex Hormozi. You are an advisor who has studied his work deeply.
- Be direct and practical, but not preachy or performative. No unnecessary hype.
- If the retrieved context doesn't cover the topic well, say so and answer based on general Hormozi principles.
- Always ground your reasoning in logic the user can follow, not just assertions.`;

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
  const { question, history } = (await req.json()) as {
    question: string;
    history?: { role: "user" | "assistant"; content: string }[];
  };

  if (!question?.trim()) {
    return new Response("Missing question", { status: 400 });
  }

  // Embed question + query Pinecone
  const embedding = await getEmbedding(question);
  const index = pc.index(process.env.PINECONE_INDEX_NAME!);
  const results = await index.query({
    vector: embedding,
    topK: 8,
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
    model: "llama-3.3-70b-versatile",
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      ...(history ?? []),
      {
        role: "user",
        content: `Context from Hormozi's content:\n\n${context}\n\n---\n\nUser's question: ${question}`,
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
