import { useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import type {
  CopilotMessage,
  CopilotReportContext,
  ExtractedParameter,
} from '../types/api';

interface Props {
  reportContext: CopilotReportContext;
}

function cleanParameterName(parameter: ExtractedParameter): string {
  const name = parameter.canonical_parameter || parameter.raw_label || 'this result';

  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function buildSuggestedQuestions(parameters: ExtractedParameter[]): string[] {
  const abnormal = parameters.filter(
    (parameter) => parameter.flag === 'high' || parameter.flag === 'low',
  );

  if (abnormal.length === 0) {
    return [
      'Give me a simple summary of my results',
      'What should I discuss with my doctor?',
      'Which results are most important to keep monitoring?',
      'Explain my report in simple terms',
    ];
  }

  const questions: string[] = [];

  abnormal.slice(0, 2).forEach((parameter) => {
    const name = cleanParameterName(parameter);
    const direction = parameter.flag === 'high' ? 'above' : 'below';

    questions.push(
      `Why is my ${name} ${direction} the reference range?`,
    );
  });

  questions.push('Which results should I discuss with my doctor?');
  questions.push('Give me a simple summary of the values needing attention');

  return questions;
}

export function CopilotPanel({ reportContext }: Props) {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const suggestedQuestions = buildSuggestedQuestions(reportContext.parameters);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({
        top: listRef.current.scrollHeight,
        behavior: 'smooth',
      });
    });
  };

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const nextMessages: CopilotMessage[] = [
      ...messages,
      { role: 'user', content: trimmed },
    ];

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

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.reply },
      ]);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : 'The Copilot is unavailable right now. Please try again.',
      );
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  return (
    <div className="card copilot-panel">
      <div className="copilot-header">
        <p className="section-title" style={{ margin: 0 }}>
          Aegis AI Copilot
        </p>
        <p className="copilot-subtitle">
          Ask questions about your report
        </p>
      </div>

      <div className="copilot-messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="copilot-empty">
            <p>
              I already understand this report&apos;s findings -- ask me anything
              about the values, flags, or reference ranges above.
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`copilot-bubble ${m.role}`}>
            {m.content}
          </div>
        ))}

        {loading && (
          <div
            className="copilot-bubble assistant copilot-typing"
            aria-live="polite"
          >
            Thinking&hellip;
          </div>
        )}
      </div>

      {error && (
        <p className="error-text copilot-error" role="alert">
          {error}
        </p>
      )}

      <div className="copilot-chips">
        {suggestedQuestions.map((question) => (
          <button
            key={question}
            type="button"
            className="copilot-chip"
            onClick={() => sendMessage(question)}
            disabled={loading}
          >
            {question}
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

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}
