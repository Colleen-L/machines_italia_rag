import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { question } = await request.json();
    if (!question?.trim()) {
      return NextResponse.json(
        { error: "Question is required" },
        { status: 400 }
      );
    }

    const n8nResponse = await fetch(
      process.env.N8N_RETRIEVAL_WEBHOOK_URL!,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
        }),
      }
    );

    if (!n8nResponse.ok) {
      const error = await n8nResponse.text();
      console.error("n8n error:", error);
      return NextResponse.json(
        { error: "n8n request failed" },
        { status: 500 }
      );
    }

    const data = await n8nResponse.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error("API error:", error);
    return NextResponse.json(
      { error: "Something went wrong" },
      { status: 500 }
    );
  }
}