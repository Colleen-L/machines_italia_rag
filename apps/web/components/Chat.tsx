"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! Ask me anything about Machines Italia.",
    },
  ]);

  const [input, setInput] = useState("");

  async function sendMessage() {
    if (!input.trim()) return;
    const question = input.trim();
    // show the user's question in the chat
    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: question,
      },
    ]);
    setInput("");
    try {
      // send the question to Next.js API route
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to get response");
      }
      const data = await response.json();
      // display n8n's answer
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.output,
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
    }
  }



  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4">
        <h1 className="text-xl font-semibold">
          Machines Italia
        </h1>
        <p className="text-sm text-gray-500">
          AI Knowledge Assistant
        </p>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={
                message.role === "user"
                  ? "ml-auto max-w-[80%] rounded-2xl bg-black px-4 py-3 text-white"
                  : "mr-auto max-w-[80%] rounded-2xl border px-4 py-3"
              }
            >
              {message.content}
            </div>
          ))}
        </div>
      </main>

      {/* Input */}
      <footer className="border-t px-6 py-4">
        <div className="mx-auto flex max-w-3xl gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                sendMessage();
              }
            }}
            placeholder="Ask a question..."
            className="flex-1 rounded-xl border px-4 py-3 outline-none focus:ring-2"
          />

          <button
            onClick={sendMessage}
            className="rounded-xl bg-black px-5 py-3 text-white"
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  );
}