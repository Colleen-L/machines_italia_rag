"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ParsedMessage = {
  content: string;
  sources: string[];
};

function parseMessage(content: string): ParsedMessage {
  const sources: string[] = [];

  // Find a "Sources:" section at the end of the response.
  const sourceMatch = content.match(
    /(?:^|\n)\s*(?:Sources?|References?)\s*:\s*([\s\S]*)$/i
  );

  let answer = content;

  if (sourceMatch) {
    answer = content.slice(0, sourceMatch.index).trim();

    const sourceText = sourceMatch[1];

    // Extract all URLs from the source section.
    const urls = sourceText.match(/https?:\/\/[^\s<>)\]]+/g) || [];

    urls.forEach((url) => {
      const cleaned = url.replace(/[.,;]+$/, "");

      if (!sources.includes(cleaned)) {
        sources.push(cleaned);
      }
    });
  }

  // Also extract markdown links from the answer.
  const markdownLinks = answer.matchAll(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g
  );

  for (const match of markdownLinks) {
    const url = match[2];

    if (!sources.includes(url)) {
      sources.push(url);
    }

    answer = answer.replace(match[0], match[1]);
  }

  return {
    content: answer.trim(),
    sources,
  };
}

function shouldShowSources(question: string): boolean {
  const normalized = question.toLowerCase().trim();

  // Conversational / non-knowledge questions should not show
  // unrelated retrieved Machines Italia sources.
  const casualPatterns = [
    /^hi\b/,
    /^hello\b/,
    /^hey\b/,
    /^thanks\b/,
    /^thank you\b/,
    /^good morning\b/,
    /^good afternoon\b/,
    /^good evening\b/,
    /^i'?m having a bad day\b/,
    /^i am having a bad day\b/,
    /^how are you\b/,
    /^what's up\b/,
    /^whats up\b/,
  ];

  if (casualPatterns.some((pattern) => pattern.test(normalized))) {
    return false;
  }

  return true;
}

function formatUrl(url: string) {
  try {
    const parsed = new URL(url);

    // Prefer a compact pathname rather than showing the entire URL.
    const path = parsed.pathname
      .replace(/^\/+/, "")
      .replace(/\/$/, "");

    if (!path) {
      return parsed.hostname;
    }

    const lastPart = path.split("/").pop() || parsed.hostname;

    return lastPart
      .replace(/[-_]/g, " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  } catch {
    return "Source";
  }
}

function renderInlineText(text: string) {
  const parts = text.split(
    /(\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^)]+\)|https?:\/\/[^\s]+)/g
  );

  return parts.map((part, index) => {
    if (!part) return null;

    // Bold
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Markdown link
    const markdownMatch = part.match(
      /^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/
    );

    if (markdownMatch) {
      return (
        <a
          key={index}
          href={markdownMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium underline underline-offset-2 hover:opacity-70"
        >
          {markdownMatch[1]}
        </a>
      );
    }

    // Plain URL
    if (part.startsWith("http://") || part.startsWith("https://")) {
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium underline underline-offset-2 hover:opacity-70"
        >
          {formatUrl(part)}
        </a>
      );
    }

    return <span key={index}>{part}</span>;
  });
}

function AnswerContent({ content }: { content: string }) {
  const lines = content.split("\n");

  return (
    <div className="space-y-3 text-[15px] leading-7 text-gray-800">
      {lines.map((line, index) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={index} className="h-1" />;
        }

        // Headings
        if (trimmed.startsWith("### ")) {
          return (
            <h3
              key={index}
              className="pt-2 text-base font-semibold text-gray-950"
            >
              {renderInlineText(trimmed.replace(/^### /, ""))}
            </h3>
          );
        }

        if (trimmed.startsWith("## ")) {
          return (
            <h2
              key={index}
              className="pt-2 text-lg font-semibold text-gray-950"
            >
              {renderInlineText(trimmed.replace(/^## /, ""))}
            </h2>
          );
        }

        // Numbered list
        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);

        if (numberedMatch) {
          return (
            <div key={index} className="flex gap-3">
              <span className="flex h-6 min-w-6 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-600">
                {numberedMatch[1]}
              </span>

              <div className="flex-1">
                {renderInlineText(numberedMatch[2])}
              </div>
            </div>
          );
        }

        // Bullet list
        const bulletMatch = trimmed.match(/^[-*•]\s+(.*)$/);

        if (bulletMatch) {
          return (
            <div key={index} className="flex gap-3">
              <span className="mt-[10px] h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400" />

              <div className="flex-1">
                {renderInlineText(bulletMatch[1])}
              </div>
            </div>
          );
        }

        return (
          <p key={index}>
            {renderInlineText(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function Sources({ urls }: { urls: string[] }) {
  if (urls.length === 0) return null;

  return (
    <div className="mt-4 border-t border-gray-100 pt-3">
      <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
        Sources
      </div>

      <div className="flex flex-wrap gap-2">
        {urls.map((url, index) => (
          <a
            key={`${url}-${index}`}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            title={url}
            className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-xs font-medium text-gray-600 transition hover:border-gray-300 hover:bg-gray-100 hover:text-gray-900"
          >
            <svg
              className="h-3.5 w-3.5 shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>

            <span className="truncate">
              {formatUrl(url)}
            </span>

            <svg
              className="h-3 w-3 shrink-0 opacity-50"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M7 17L17 7" />
              <path d="M7 7h10v10" />
            </svg>
          </a>
        ))}
      </div>
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! Ask me anything about Machines Italia.",
    },
  ]);

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function sendMessage() {
    if (!input.trim() || isLoading) return;

    const question = input.trim();

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: question,
      },
    ]);

    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            data.output ||
            "Sorry, I couldn't find an answer to that question.",
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "Sorry, I couldn't get an answer right now.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-white">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/95 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-black text-sm font-bold text-white">
            MI
          </div>

          <div>
            <h1 className="text-base font-semibold text-gray-950">
              Machines Italia
            </h1>

            <p className="text-xs text-gray-500">
              AI Knowledge Assistant
            </p>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-8 sm:px-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-8">
          {messages.map((message, index) => {
            const parsed =
              message.role === "assistant"
                ? parseMessage(message.content)
                : {
                    content: message.content,
                    sources: [],
                  };

            const showSources =
              message.role === "assistant" &&
              shouldShowSources(
                index > 0 ? messages[index - 1]?.content || "" : ""
              );

            return (
              <div key={index} className="w-full">
                {message.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl bg-black px-4 py-3 text-sm leading-6 text-white shadow-sm">
                      {message.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <div className="max-w-[90%] rounded-2xl border border-gray-200 bg-gray-50 px-5 py-4 shadow-sm">
                      <AnswerContent content={parsed.content} />

                      {showSources && <Sources urls={parsed.sources} />}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <div className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-gray-400" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-gray-400 [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-gray-400 [animation-delay:300ms]" />
              </div>

              <span>Thinking...</span>
            </div>
          )}
        </div>
      </main>

      {/* Input */}
      <footer className="sticky bottom-0 border-t border-gray-200 bg-white px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-center gap-2 rounded-2xl border border-gray-300 bg-white p-1.5 shadow-sm transition focus-within:border-gray-500 focus-within:ring-2 focus-within:ring-gray-100">
            <input
              value={input}
              disabled={isLoading}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Ask a question about Machines Italia..."
              className="min-w-0 flex-1 bg-transparent px-3 py-2.5 text-sm outline-none placeholder:text-gray-400 disabled:cursor-not-allowed disabled:opacity-50"
            />

            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="flex h-10 items-center justify-center rounded-xl bg-black px-4 text-sm font-medium text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400"
            >
              {isLoading ? (
                <svg
                  className="h-4 w-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="9"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="opacity-25"
                  />
                  <path
                    d="M21 12a9 9 0 0 0-9-9"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                </svg>
              ) : (
                "Send"
              )}
            </button>
          </div>

          <p className="mt-2 text-center text-xs text-gray-400">
            Machines Italia AI Knowledge Assistant
          </p>
        </div>
      </footer>
    </div>
  );
}