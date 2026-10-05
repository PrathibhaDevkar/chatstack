import { useEffect, useRef, useState } from "react";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  // Load chat history once when the page opens
  useEffect(() => {
    fetch("/api/messages")
      .then((r) => r.json())
      .then(setMessages)
      .catch(() => setError("Could not load history"));
  }, []);

  // Keep the newest message in view
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", content: data.answer }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>ChatStack</h1>
        <span>llama3.2:1b · running in Docker</span>
      </header>
      <main className="chat">
        {messages.map((m, i) => (
          <div key={m.id ?? i} className={`msg ${m.role}`}>{m.content}</div>
        ))}
        {loading && <div className="msg assistant">Thinking…</div>}
        <div ref={bottomRef} />
      </main>
      {error && <p className="error">{error}</p>}
      <form onSubmit={send}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything…"
          autoFocus
        />
        <button disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}