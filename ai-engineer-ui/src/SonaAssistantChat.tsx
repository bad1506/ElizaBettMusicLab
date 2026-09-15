import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { ArrowUp, Bot, Sparkles, X } from "lucide-react";
import "./SonaAssistantChat.css";

type ChatMessage = { role: "user" | "assistant"; text: string };

const initial: ChatMessage[] = [{ role: "assistant", text: "Привет. Я SØNA Assistant. Здесь можно просто общаться со мной: придумать песню, разобрать идею, помочь с текстом, релизом, продвижением или разобраться с любым вопросом по SØNA." }];

export default function SonaAssistantChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(initial);
  const [busy, setBusy] = useState(false);
  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    const history = messages.slice(-20);
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const token = localStorage.getItem("sona_token");
      const response = await fetch("/api/sona-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ message: text, history, context: { product: "SØNA", language: "ru", client: "web" } }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data?.detail || "Не удалось получить ответ");
      setMessages((prev) => [...prev, { role: "assistant", text: data.answer || "Не удалось получить ответ." }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: "assistant", text: error instanceof Error ? `Не удалось ответить: ${error.message}` : "Не удалось ответить. Попробуй ещё раз." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`sona-assistant ${open ? "is-open" : ""}`}>
      {open && (
        <section className="sona-chat-panel" aria-label="SØNA Assistant">
          <header className="sona-chat-header">
            <div className="sona-chat-identity"><div className="sona-chat-icon"><Bot size={19} /></div><div><strong>SØNA Assistant</strong><span><i /> online</span></div></div>
            <button className="sona-chat-close" onClick={() => setOpen(false)} aria-label="Закрыть"><X size={18} /></button>
          </header>
          <div className="sona-chat-messages">
            {messages.map((message, index) => <div key={`${message.role}-${index}`} className={`sona-chat-message ${message.role}`}>{message.text}</div>)}
            {busy && <div className="sona-chat-message assistant typing"><span /><span /><span /></div>}
          </div>
          <form className="sona-chat-composer" onSubmit={send}>
            <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Напиши сообщение…" aria-label="Сообщение" autoFocus />
            <button type="submit" disabled={!canSend} aria-label="Отправить"><ArrowUp size={17} /></button>
          </form>
          <div className="sona-chat-hint">SØNA — твой AI-помощник для музыки, идей и работы над релизом.</div>
        </section>
      )}
      {!open && <button className="sona-chat-trigger" onClick={() => setOpen(true)}><Sparkles size={18} /><span>Чат SØNA</span></button>}
    </div>
  );
}
