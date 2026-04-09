"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";

const GoogleAddressInput = dynamic(() => import("../components/GoogleAddressInput"), {
  ssr: false,
});

const HAS_MAPS_KEY = !!process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

type Role = "user" | "assistant";

interface Message {
  role: Role;
  content: string;
  streaming?: boolean;
}




const PROMPTS = [
  "What can I eat for lunch near me?",
  "Find me a safe dinner option nearby",
  "Which restaurants have the most options for me?",
  "What should I avoid ordering?",
];

type StoredProfile = {
  fullName: string;
  sexGender: string;
  location: string;
  conditions: string[];
  allergies: string[];
  profileComplete?: true;
};

export default function ChatPage() {
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<"landing" | "chat">("landing");

  const [distance, setDistance] = useState(5);
  const [searchAddress, setSearchAddress] = useState("");
  const [editingAddress, setEditingAddress] = useState(false);
  const [draftAddress, setDraftAddress] = useState("");
  const [showMapPicker, setShowMapPicker] = useState(false);

  const [profile, setProfile] = useState<StoredProfile | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const addressInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("userProfile");
      if (!stored) {
        router.replace("/profile");
        return;
      }
      const p: StoredProfile = JSON.parse(stored);
      if (!p.profileComplete) {
        router.replace("/profile");
        return;
      }
      setProfile(p);
      if (p.location) setSearchAddress(p.location);
    } catch {
      router.replace("/profile");
    }
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (editingAddress) {
      addressInputRef.current?.select();
    }
  }, [editingAddress]);

  const startEditing = () => {
    setDraftAddress(searchAddress);
    setEditingAddress(true);
  };

  const commitAddress = () => {
    const trimmed = draftAddress.trim();
    if (trimmed) {
      setSearchAddress(trimmed);
    }
    setEditingAddress(false);
  };

  const handleAddressKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitAddress();
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setEditingAddress(false);
    }
  };

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    autoResize(e.target);
  };

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || loading) return;

      const userMsg: Message = { role: "user", content: text.trim() };
      const nextMessages = [...messages, userMsg];

      setMessages(nextMessages);
      setInput("");
      setLoading(true);
      setPhase("chat");

      if (textareaRef.current) textareaRef.current.style.height = "auto";

      setMessages((prev) => [...prev, { role: "assistant", content: "", streaming: true }]);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      try {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: nextMessages.map((m) => ({ role: m.role, content: m.content })),
            location: searchAddress,
            radius_miles: distance,
            conditions: profile?.conditions ?? [],
            allergies: profile?.allergies ?? [],
          }),
          signal: ctrl.signal,
        });

        if (!res.ok || !res.body) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail ?? `Server error ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let tokensStarted = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (raw === "[DONE]") break;

            try {
              const evt = JSON.parse(raw);

              if (evt.error) throw new Error(evt.error);

              if (evt.type === "status") {
                if (!tokensStarted) {
                  setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                      updated[updated.length - 1] = { ...last, content: evt.message ?? "", streaming: true };
                    }
                    return updated;
                  });
                }

              } else if (evt.type === "token") {
                if (!tokensStarted) {
                  tokensStarted = true;
                  setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                      updated[updated.length - 1] = { ...last, content: "", streaming: true };
                    }
                    return updated;
                  });
                }
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last?.role === "assistant") {
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + evt.token,
                      streaming: true,
                    };
                  }
                  return updated;
                });

              } else if (evt.token) {
                if (!tokensStarted) {
                  tokensStarted = true;
                  setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                      updated[updated.length - 1] = { ...last, content: "", streaming: true };
                    }
                    return updated;
                  });
                }
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last?.role === "assistant") {
                    updated[updated.length - 1] = { ...last, content: last.content + evt.token, streaming: true };
                  }
                  return updated;
                });
              }
            } catch (parseErr) {
              if (parseErr instanceof Error && parseErr.name !== "SyntaxError") throw parseErr;
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        const msg = err instanceof Error ? err.message : "Something went wrong.";
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { role: "assistant", content: `Error: ${msg}`, streaming: false };
          }
          return updated;
        });
      } finally {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, streaming: false };
          }
          return updated;
        });
        setLoading(false);
        abortRef.current = null;
      }
    },
    [messages, loading, searchAddress, distance, profile]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const overlayControls = (
    <>
      {showMapPicker && (
        <GoogleAddressInput
          onSelect={(address) => {
            setSearchAddress(address);
            setDraftAddress(address);
            setShowMapPicker(false);
          }}
          onCancel={() => setShowMapPicker(false)}
        />
      )}

      <div className="discover-distance-control">
        <div className="distance-header">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="10" r="3" />
            <path d="M12 2a8 8 0 0 1 8 8c0 5.25-8 13-8 13S4 15.25 4 10a8 8 0 0 1 8-8z" />
          </svg>
          <span>
            Within <strong>{distance} mi</strong>
          </span>
        </div>
        <input
          type="range"
          min={1}
          max={25}
          step={1}
          value={distance}
          onChange={(e) => setDistance(Number(e.target.value))}
          className="distance-slider"
          aria-label="Search radius in miles"
          style={{
            background: `linear-gradient(to right, var(--brand) ${((distance - 1) / 24) * 100}%, var(--line) ${((distance - 1) / 24) * 100}%)`,
          }}
        />
        <div className="distance-range-labels">
          <span>1 mi</span>
          <span>25 mi</span>
        </div>
      </div>

      <div className="discover-address-badge">
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          style={{ flexShrink: 0 }}
        >
          <circle cx="12" cy="10" r="3" />
          <path d="M12 2a8 8 0 0 1 8 8c0 5.25-8 13-8 13S4 15.25 4 10a8 8 0 0 1 8-8z" />
        </svg>

        {editingAddress ? (
          <div className="address-edit-row">
            <input
              ref={addressInputRef}
              className="address-edit-input"
              value={draftAddress}
              onChange={(e) => setDraftAddress(e.target.value)}
              onKeyDown={handleAddressKey}
              onBlur={commitAddress}
              placeholder="123 Main St, City, State"
              aria-label="Search address"
            />
            {HAS_MAPS_KEY && (
              <button
                className="address-map-btn"
                onMouseDown={(e) => {
                  e.preventDefault();
                  setEditingAddress(false);
                  setShowMapPicker(true);
                }}
                title="Search with Google Maps"
                aria-label="Open map picker"
              >
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </button>
            )}
            <button
              className="address-edit-confirm"
              onMouseDown={(e) => {
                e.preventDefault();
                commitAddress();
              }}
              aria-label="Confirm"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </button>
          </div>
        ) : (
          <button
            className="address-display-btn"
            onClick={startEditing}
            title="Click to change search address"
          >
            <span className="address-text">{searchAddress || "Set search address"}</span>
            <svg
              width="11"
              height="11"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              style={{ flexShrink: 0, opacity: 0.5 }}
            >
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
        )}
      </div>
    </>
  );

  if (phase === "landing") {
    return (
      <main className="chat-landing">
        {overlayControls}

        <div className="chat-landing-inner">
          <div className="chat-landing-icon" aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H9l-4 4V6Z" stroke="currentColor" strokeWidth="1.8" />
              <circle cx="9" cy="10" r="1" fill="currentColor" />
              <circle cx="12" cy="10" r="1" fill="currentColor" />
              <circle cx="15" cy="10" r="1" fill="currentColor" />
            </svg>
          </div>

          <p className="eyebrow">Dining assistant</p>
          <h1 className="chat-landing-heading">
            Ask a question and get personalized food guidance
          </h1>
          <p className="chat-landing-sub">
            Request local restaurant ideas, ingredient checks, or meal suggestions that align
            with your profile.
          </p>

          <div className="chat-input-box">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder="For example: What are strong gluten-free options near downtown?"
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              rows={1}
              autoFocus
              aria-label="Chat input"
            />
            <button
              className="chat-send-btn"
              disabled={!input.trim() || loading}
              onClick={() => sendMessage(input)}
              aria-label="Send"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </div>

          <p className="chat-hint">Press Enter to send and Shift+Enter for a new line.</p>

          <div className="chat-suggestions">
            {PROMPTS.map((prompt) => (
              <button
                key={prompt}
                className="chat-suggestion-pill"
                onClick={() => sendMessage(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="chat-page">
      {overlayControls}

      <header className="chat-topbar">
        <div className="chat-topbar-inner">
          <p className="chat-topbar-title">Assistant conversation</p>
          <p className="chat-topbar-sub">Guidance based on your saved profile and current radius.</p>
        </div>
      </header>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`chat-bubble-row ${
              msg.role === "user" ? "chat-bubble-row--user" : "chat-bubble-row--assistant"
            }`}
          >
            {msg.role === "assistant" && (
              <div className="chat-avatar" aria-hidden="true">
                N
              </div>
            )}
            <div
              className={`chat-bubble ${
                msg.role === "user" ? "chat-bubble--user" : "chat-bubble--assistant"
              }`}
            >
              <MessageContent content={msg.content} streaming={msg.streaming} />
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <div className="chat-input-box">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Ask a follow-up question"
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
            aria-label="Chat input"
          />
          <button
            className="chat-send-btn"
            disabled={!input.trim() || loading}
            onClick={() => sendMessage(input)}
            aria-label="Send"
          >
            {loading ? (
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="spin"
              >
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
            ) : (
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            )}
          </button>
        </div>
        <p className="chat-hint">Press Enter to send and Shift+Enter for a new line.</p>
      </div>
    </main>
  );
}

function MessageContent({ content, streaming }: { content: string; streaming?: boolean }) {
  if (!content && streaming) {
    return <span className="chat-cursor" aria-label="typing" />;
  }

  const parts = content.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  const nodes = parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="chat-inline-code">
          {part.slice(1, -1)}
        </code>
      );
    }
    return part.split("\n").map((line, j, arr) => (
      <span key={`${i}-${j}`}>
        {line}
        {j < arr.length - 1 && <br />}
      </span>
    ));
  });

  return (
    <>
      {nodes}
      {streaming && <span className="chat-cursor" aria-hidden="true" />}
    </>
  );
}
