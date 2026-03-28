"use client";

import { useState, useRef, useEffect } from "react";

type Source = { title: string; url: string };
type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  streaming?: boolean;
};

const SUGGESTIONS = [
  "How do I get my first 10 customers?",
  "How should I price my offer?",
  "What's the biggest mistake new business owners make?",
  "How do I hire the right people?",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMessage: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    const assistantMessage: Message = {
      role: "assistant",
      content: "",
      streaming: true,
    };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!res.ok) throw new Error("Request failed");

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let firstLine = true;
      let sources: Source[] = [];
      let content = "";
      let buffer = "";

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        if (firstLine) {
          const newlineIdx = buffer.indexOf("\n");
          if (newlineIdx !== -1) {
            const jsonLine = buffer.slice(0, newlineIdx);
            buffer = buffer.slice(newlineIdx + 1);
            firstLine = false;
            try {
              const parsed = JSON.parse(jsonLine);
              sources = parsed.sources ?? [];
            } catch {}
          } else {
            continue;
          }
        }

        content += buffer;
        buffer = "";

        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: "assistant", content, sources, streaming: true },
        ]);
      }

      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content, sources, streaming: false },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content: "Something went wrong. Please try again.",
          streaming: false,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(input);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0a]">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10">
        <div className="w-8 h-8 rounded-full bg-brand flex items-center justify-center text-black font-bold text-sm">
          H
        </div>
        <div>
          <h1 className="text-white font-semibold text-sm">Hormozi AI</h1>
          <p className="text-white/40 text-xs">Business advice based on Alex Hormozi&apos;s content</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 chat-scroll">
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-10 mt-8">
              <div className="w-16 h-16 rounded-full bg-brand/20 border border-brand/30 flex items-center justify-center mx-auto mb-4">
                <span className="text-brand text-2xl font-bold">H</span>
              </div>
              <h2 className="text-white text-xl font-semibold mb-2">
                Ask Hormozi Anything
              </h2>
              <p className="text-white/40 text-sm max-w-sm mx-auto">
                Get business advice based on thousands of hours of Alex Hormozi&apos;s content.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSubmit(s)}
                  className="text-left p-4 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-brand/40 transition-all text-white/70 text-sm"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-2xl mx-auto flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-full bg-brand flex items-center justify-center text-black font-bold text-xs mr-3 mt-1 flex-shrink-0">
                H
              </div>
            )}

            <div className={`max-w-[85%] ${msg.role === "user" ? "ml-12" : ""}`}>
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-white/10 text-white rounded-tr-sm"
                    : "bg-[#141414] text-white/90 rounded-tl-sm border border-white/5"
                } ${msg.streaming ? "cursor" : ""}`}
              >
                {msg.content || (msg.streaming ? "" : "...")}
              </div>

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && !msg.streaming && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {msg.sources.slice(0, 3).map((src, j) => (
                    <a
                      key={j}
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-brand/70 hover:text-brand border border-brand/20 hover:border-brand/40 rounded-full px-3 py-1 transition-colors truncate max-w-[200px]"
                      title={src.title}
                    >
                      {src.title.length > 30
                        ? src.title.slice(0, 30) + "…"
                        : src.title}
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-4 border-t border-white/10">
        <div className="max-w-2xl mx-auto flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a business question..."
            rows={1}
            disabled={loading}
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm placeholder-white/30 focus:outline-none focus:border-brand/50 resize-none disabled:opacity-50 max-h-32 overflow-y-auto"
            style={{ lineHeight: "1.5" }}
          />
          <button
            onClick={() => handleSubmit(input)}
            disabled={!input.trim() || loading}
            className="w-10 h-10 rounded-xl bg-brand hover:bg-brand/80 disabled:bg-white/10 disabled:cursor-not-allowed transition-colors flex items-center justify-center flex-shrink-0"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>
        <p className="text-center text-white/20 text-xs mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
