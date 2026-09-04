import { useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import type { CopilotMessage, CopilotReportContext } from '../types/api';

const SUGGESTED_QUESTIONS = [
  'Explain my abnormal results',
  'What should I discuss with my doctor?',
  'Why is my triglyceride high?',
  'Give me a simple summary',
];

interface Props {
  reportContext: CopilotReportContext;
}

export function CopilotPanel({ reportContext }: Props) {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
    });
  };

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const nextMessages: CopilotMessage[] = [...messages, { role: 'user', content: trimmed }];
    setMessages(nextMessages);
    setInput('');
    setError(null);
    setLoading(true);
    scrollToBottom();

    try {
      const res = await api.copilotChat({
        message: trimmed,
        report_context: reportContext,
        history: nextMessages.slice(0, -1),
      });
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'The Copilot is unavailable right now. Please try again.');
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  return (
    <div className="card copilot-panel">
      <div className="copilot-header">
        <p className="section-title" style={{ margin: 0 }}>Aegis AI Copilot</p>
        <p className="copilot-subtitle">Ask questions about your report</p>
      </div>

      <div className="copilot-messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="copilot-empty">
            <p>
              I already understand this report's findings -- ask me anything about the values,
              flags, or reference ranges above.
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`copilot-bubble ${m.role}`}>
            {m.content}
          </div>
        ))}

        {loading && (
          <div className="copilot-bubble assistant copilot-typing" aria-live="polite">
            Thinking&hellip;
          </div>
        )}
      </div>

      {error && <p className="error-text copilot-error" role="alert">{error}</p>}

      <div className="copilot-chips">
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            className="copilot-chip"
            onClick={() => sendMessage(q)}
            disabled={loading}
          >
            {q}
          </button>
        ))}
      </div>

      <form
        className="copilot-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage(input);
        }}
      >
        <input
          type="text"
          className="text-input"
          placeholder="Ask about your results…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
