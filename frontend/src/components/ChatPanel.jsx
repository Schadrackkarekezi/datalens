import { useState } from "react";
import ResultsTable from "./ResultsTable";
import { askQuestion } from "../api";

function Exchange({ entry }) {
  const [showContext, setShowContext] = useState(false);
  const { question, error, data } = entry;

  return (
    <div className="chat-exchange">
      <div className="chat-question">{question}</div>

      {error && <div className="error-banner">{error}</div>}

      {data && (
        <div className="chat-answer">
          {data.retrieved_context.length > 0 && (
            <div className="chat-context">
              <button className="chat-context-toggle" onClick={() => setShowContext((v) => !v)}>
                {showContext ? "▼" : "▶"} Retrieved context ({data.retrieved_context.length})
              </button>
              {showContext && (
                <ul>
                  {data.retrieved_context.map((c) => (
                    <li key={c.term}>
                      <strong>{c.term}</strong>: {c.definition}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="chat-sql">
            <div className="chat-sql-label">
              Generated SQL{data.attempts > 1 ? ` (took ${data.attempts} attempts)` : ""}
            </div>
            <pre>{data.generated_sql}</pre>
          </div>

          <ResultsTable result={data} loading={false} />
        </div>
      )}
    </div>
  );
}

export default function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim() || loading) return;
    const q = question;
    setQuestion("");
    setLoading(true);

    try {
      const data = await askQuestion(q);
      setHistory((prev) => [...prev, { question: q, data }]);
    } catch (err) {
      setHistory((prev) => [...prev, { question: q, error: err.message }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-history">
        {history.length === 0 && (
          <div className="chat-empty">
            Ask a question in plain English — e.g. "What's our win rate by department?"
          </div>
        )}
        {history.map((entry, i) => (
          <Exchange key={i} entry={entry} />
        ))}
        {loading && (
          <div className="chat-exchange">
            <div className="chat-question">{question || "…"}</div>
            <div className="chat-thinking">
              <span className="spinner" /> thinking…
            </div>
          </div>
        )}
      </div>
      <div className="chat-input-row">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your data…"
          rows={2}
        />
        <button className="run-btn" onClick={handleAsk} disabled={loading}>
          {loading ? <span className="spinner" /> : "Ask"}
        </button>
      </div>
    </div>
  );
}
