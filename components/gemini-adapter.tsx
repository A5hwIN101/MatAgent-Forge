// components/gemini-adapter.ts
// Thin adapter: convert a text -> backend POST and return markdown/text result.
// No AI SDK. Minimal, deterministic.

export type AdapterResponse = {
  ok: boolean;
  markdown: string;
  raw?: any;
  error?: string;
};

// 🛑 CRITICAL FIX: Use the live Render URL for deployment
const BACKEND_URL = "https://matagent-forge-api.onrender.com";
// You can comment this out and use: const BACKEND_URL = "http://localhost:8000"; for local dev.

export async function sendMessageToBackend(message: string): Promise<AdapterResponse> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ material_name: message }),
    });

    const text = await res.text();

    // Try JSON parse, prefer `markdown` or `markdown_output` fields if present
    try {
      const j = JSON.parse(text);
      const md = j.markdown || j.markdown_output || (typeof j === "string" ? j : JSON.stringify(j, null, 2));
      return { ok: true, markdown: md, raw: j };
    } catch {
      // Not JSON, treat as raw markdown/text
      return { ok: res.ok, markdown: text, raw: text };
    }
  } catch (err: any) {
    return { ok: false, markdown: `⚠️ Failed to contact backend: ${err?.message || err}`, error: err?.message || String(err) };
  }
}