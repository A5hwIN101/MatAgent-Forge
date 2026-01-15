'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, User, Atom } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { sendMessageToBackend } from '@/components/gemini-adapter';

// --- TYPES ---
type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

// --- LOADING ANIMATION ---
function LoadingIndicator() {
  const [frame, setFrame] = useState(0);
  const [msgIndex, setMsgIndex] = useState(0);
  const brailleFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  const statusMessages = ["Accessing Materials Project...", "Normalizing Crystal Structure...", "Running Hypothesis Engine...", "Streaming Response..."];

  useState(() => {
    const timer = setInterval(() => setFrame((prev) => (prev + 1) % brailleFrames.length), 80);
    return () => clearInterval(timer);
  });

  useState(() => {
    const timer = setInterval(() => setMsgIndex((prev) => (prev + 1) % statusMessages.length), 800);
    return () => clearInterval(timer);
  });

  return (
    <div className="flex gap-4 max-w-4xl mx-auto justify-start">
      <div className="w-8 h-8 rounded-full bg-gray-800 flex-shrink-0" />
      <div className="px-5 py-4 text-gray-400 text-sm font-mono flex items-center gap-3">
        <span className="text-lg leading-none">{brailleFrames[frame]}</span>
        <span>{statusMessages[msgIndex]}</span>
      </div>
    </div>
  );
}

// --- MAIN COMPONENT ---
export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // --- SMART SCROLL REFS ---
  const [isAtBottom, setIsAtBottom] = useState(true); // Track if we should auto-scroll
  const messagesEndRef = useRef<HTMLDivElement>(null); // The invisible anchor
  const scrollContainerRef = useRef<HTMLDivElement>(null); // The scrollable area

  const isChatStarted = messages.length > 0;

  // 1. SCROLL EFFECT: Fires whenever messages change (streaming or new)
  useEffect(() => {
    // Only scroll if the user hasn't scrolled up
    if (isAtBottom && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isAtBottom, isLoading]);

  // 2. SCROLL HANDLER: Detects if user moved up
  const handleScroll = () => {
    const div = scrollContainerRef.current;
    if (!div) return;

    // Tolerance of 50px (are we near the bottom?)
    const isNearBottom = div.scrollHeight - div.scrollTop - div.clientHeight < 50;
    
    // Only update state if it changed to prevent re-render loops
    if (isNearBottom !== isAtBottom) {
      setIsAtBottom(isNearBottom);
    }
  };

  const cleanResponse = (text: string) => {
    if (!text) return "";
    let cleaned = text
      .replace(/🔹 Step \d+:.*(\r\n|\n|\r|$)/g, "")
      .replace(/🔹 Database miss.*(\r\n|\n|\r|$)/g, "")
      .replace(/Step \d+:.*(\r\n|\n|\r|$)/g, "")
      .replace(/^\s*[\r\n]/gm, "")
      .trim();

    cleaned = cleaned.replace(/\b(\d+\.\d{5,})\b/g, (match) => {
      return parseFloat(match).toFixed(4);
    });

    return cleaned;
  };

  const simulateStreaming = async (fullText: string) => {
    const botMsgId = (Date.now() + 1).toString();
    const botMsg: Message = { id: botMsgId, role: 'assistant', content: '' };
    setMessages((prev) => [...prev, botMsg]);
    setIsLoading(false);

    const chunks = fullText.split(/(\s+)/); 
    let accumulatedText = "";

    for (let i = 0; i < chunks.length; i++) {
      accumulatedText += chunks[i];
      setMessages((prev) => prev.map(msg => msg.id === botMsgId ? { ...msg, content: accumulatedText } : msg));
      await new Promise(resolve => setTimeout(resolve, Math.random() * 20 + 10));
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    // FORCE SCROLL TO BOTTOM ON SEND
    setIsAtBottom(true);

    const userText = input.trim();
    setInput('');
    setIsLoading(true);

    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: userText }]);

    try {
      const response = await sendMessageToBackend(userText);
      const rawContent = response.markdown || "";

      const errorKeywords = ["Data lookup failed", "server does not support", "Internal Server Error", "Connection refused"];
      const isBackendError = errorKeywords.some(keyword => rawContent.includes(keyword)) || !response.ok;

      if (isBackendError) {
        await simulateStreaming(
          "⚠️ **System Notice:** I encountered a technical issue while querying the database for this material.\n\nPlease check the formula and try again, or try a simpler compound (e.g., **NaCl**, **MgO**)."
        );
        return;
      }

      let cleanContent = cleanResponse(rawContent);
      if (!cleanContent || cleanContent === "{}" || cleanContent.trim() === "") {
        cleanContent = "⚠️ **Input Error:** I could not identify this material.\n\nPlease check the chemical formula (e.g., **NaCl**, **Fe2O3**) to ensure it is spelled correctly and try again.";
      }

      await simulateStreaming(cleanContent);

    } catch (error) {
      console.error("Critical Frontend Failure:", error);
      setIsLoading(false);
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "An unexpected error occurred. Please refresh the page and try again."
      }]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-black text-gray-100 font-mono selection:bg-[#8D312C] selection:text-white">
      
      {!isChatStarted && (
        <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-8 animate-in fade-in duration-500">
          <div className="p-4 bg-gray-900 rounded-2xl border border-gray-800 shadow-2xl">
            <Atom className="w-16 h-16 text-red-500" />
          </div>
          <h1 className="text-2xl md:text-3xl font-semibold text-white tracking-tight">
            How can I help you discover today?
          </h1>
          
          <div className="w-full max-w-2xl relative group">
             <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter a material formula (e.g. FeBO3)..."
              disabled={isLoading}
              rows={1}
              autoFocus
              className="w-full bg-gray-900 text-white placeholder-gray-500 border border-gray-700 rounded-2xl pl-6 pr-14 py-4 focus:outline-none focus:ring-1 focus:ring-red-500 focus:bg-gray-800 transition-all resize-none overflow-hidden min-h-[60px] text-lg shadow-lg caret-[#8D312C]"
            />
            <button onClick={() => handleSubmit()} disabled={!input.trim()} className="absolute right-3 top-3 p-2 bg-white text-black rounded-xl hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
              <Send className="w-5 h-5" />
            </button>
            <div className="text-center mt-4 text-xs text-gray-600">
              MatAgent-Forge v1.0 • Powered by Local Python Engine
            </div>
          </div>
        </div>
      )}

      {isChatStarted && (
        <>
          <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-black/50 backdrop-blur sticky top-0 z-10">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-gray-800 rounded-lg border border-gray-700">
                <Atom className="w-6 h-6 text-red-500" />
              </div>
              <h1 className="text-lg font-semibold tracking-tight text-white">MatAgent-Forge</h1>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500 font-mono border border-gray-800 px-2 py-1 rounded-md">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              System Online
            </div>
          </header>

          <div 
            className="flex-1 overflow-y-auto p-4 md:p-6 space-y-8" 
            ref={scrollContainerRef} // Attached ref to container
            onScroll={handleScroll}  // Attached scroll listener
          >
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center flex-shrink-0 border border-gray-700 mt-1">
                    <Atom className="w-5 h-5 text-red-500" />
                  </div>
                )}
                
                <div className={`relative px-5 py-3.5 text-sm leading-relaxed shadow-sm max-w-[85%] md:max-w-[75%] 
                  ${msg.role === 'user' 
                    ? 'bg-white text-black font-medium rounded-2xl' 
                    : 'bg-transparent text-gray-200 border border-gray-800 rounded-2xl'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-800">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                        table: ({node, ...props}) => <div className="overflow-x-auto my-4 rounded-lg border border-gray-800"><table className="min-w-full text-left text-sm" {...props} /></div>,
                        thead: ({node, ...props}) => <thead className="bg-gray-900 font-medium" {...props} />,
                        th: ({node, ...props}) => <th className="px-4 py-3 border-b border-gray-800 text-gray-300" {...props} />,
                        td: ({node, ...props}) => <td className="px-4 py-3 border-b border-gray-800 text-gray-400 font-mono" {...props} />,
                        code: ({node, ...props}) => <code className="bg-gray-800 px-1 py-0.5 rounded text-gray-300 font-mono text-xs border border-gray-700" {...props} />
                      }}>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
                
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 mt-1">
                    <User className="w-4 h-4 text-black" />
                  </div>
                )}
              </div>
            ))}
            {isLoading && <LoadingIndicator />}
            
            {/* INVISIBLE ANCHOR FOR SCROLLING */}
            <div ref={messagesEndRef} className="h-1" />
          </div>

          <div className="p-4 bg-black border-t border-gray-800">
            <div className="max-w-3xl mx-auto relative group">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Send a material formula..."
                disabled={isLoading}
                rows={1}
                autoFocus
                className="w-full bg-gray-900/50 text-white placeholder-gray-500 border border-gray-800 rounded-2xl pl-4 pr-12 py-3.5 focus:outline-none focus:ring-1 focus:ring-gray-600 focus:bg-gray-900 transition-all resize-none overflow-hidden min-h-[52px] caret-[#8D312C]"
              />
              <button onClick={() => handleSubmit()} disabled={!input.trim() || isLoading} className="absolute right-2 top-2 p-2 bg-white text-black rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                <Send className="w-4 h-4" />
              </button>
            </div>
            <div className="text-center mt-3 text-[11px] text-gray-600 font-medium">MatAgent-Forge v1.0 • Powered by Local Python Engine</div>
          </div>
        </>
      )}
    </div>
  );
}