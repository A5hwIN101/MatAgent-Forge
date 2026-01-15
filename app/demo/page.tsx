'use client';

import { useState } from 'react';
import { sendMessageToBackend } from '@/components/gemini-adapter';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function DemoPage() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<{ role: 'user'|'bot', text: string }[]>([]);

  const send = async () => {
    const t = input.trim();
    if (!t) return;
    setHistory(h => [...h, { role: 'user', text: t }]);
    setInput('');
    setLoading(true);
    const r = await sendMessageToBackend(t);
    setLoading(false);
    setHistory(h => [...h, { role: 'bot', text: r.markdown || (r.error ?? 'No response') }]);
  };

  return (
    <div className="min-h-screen p-6 bg-terminal-bg text-terminal-fg font-mono">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Demo — Gemini UI Adapter</h1>

        <div className="space-y-4 mb-4">
          {history.map((m, i) => (
            <div key={i} className={`p-3 rounded ${m.role === 'user' ? 'bg-accent text-white' : 'bg-terminal-bg border border-terminal-border'}`}>
              {m.role === 'bot' ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
              ) : (
                <pre className="whitespace-pre-wrap">{m.text}</pre>
              )}
            </div>
          ))}

          {loading && <div className="p-3 text-sm text-terminal-fg/70">Loading...</div>}
        </div>

        <div className="flex gap-2">
          <input
            className="flex-1 px-3 py-2 bg-terminal-bg border border-terminal-border rounded text-terminal-fg"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter material (e.g., CuCl)"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
          />
          <button onClick={send} disabled={!input.trim() || loading} className="px-4 py-2 rounded bg-accent text-white">
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
