import { useState } from "react";
import ResultsTable from "./ResultsTable";
import ReasoningTrace from "./ReasoningTrace";
import { askQuestion, clearConversation } from "../api";

const SUGGESTIONS = [
  "What is our win rate?",
  "What's our current pipeline value?",
  "Which employees logged the most activities on deals for the Analytics Suite product?",
  "How many calls were logged for deals belonging to SaaS customers?",
  "What's our customer churn rate?",
];

function newConversationId() {
  return crypto.randomUUID();
}

function Exchange({ entry }) {
  const { question, error, data } = entry;

  return (
    <div className="chat-exchange">
      <div className="chat-question">
        <span className="chat-avatar user">Y</span>
        {question}
      </div>

      {error && (
        <div className="chat-answer">
          <span className="chat-avatar agent">AI</span>
          <div className="error-banner">{error}</div>
        </div>
      )}

      {data && (
        <div className="chat-answer">
          <span className="chat-avatar agent">AI</span>
          <div className="chat-answer-body">
            <ReasoningTrace trace={data.trace} />

            {data.response_type === "chat" ? (
              <div className="chat-reply">
                <p>{data.message}</p>
                <span className="chat-cost">
                  {data.prompt_tokens + data.completion_tokens} tokens · $
                  {data.estimated_cost_usd.toFixed(5)}
                </span>
              </div>
            ) : (
              <>
                <div className="chat-sql">
                  <div className="chat-sql-label">
                    Generated SQL{data.attempts > 1 ? ` (took ${data.attempts} attempts)` : ""}
                    <span className="chat-cost">
                      {data.prompt_tokens + data.completion_tokens} tokens · $
                      {data.estimated_cost_usd.toFixed(5)}
                    </span>
                  </div>
                  <pre>{data.generated_sql}</pre>
                </div>

                <ResultsTable result={data} loading={false} />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(newConversationId);

  const send = async (q) => {
    if (!q.trim() || loading) return;
    setQuestion("");
    setLoading(true);

    try {
      const data = await askQuestion(q, conversationId);
      setHistory((prev) => [...prev, { question: q, data }]);
    } catch (err) {
      setHistory((prev) => [...prev, { question: q, error: err.message }]);
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = () => send(question);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const handleNewConversation = () => {
    clearConversation(conversationId);
    setConversationId(newConversationId());
    setHistory([]);
  };

  return (
    <div className="chat-panel">
      <div className="chat-toolbar">
        <span className="chat-toolbar-hint">
          {history.length > 0 ? "Follow-up questions use this conversation's context" : "Ask in plain English"}
        </span>
        {history.length > 0 && (
          <button className="new-conversation-btn" onClick={handleNewConversation}>
            + New conversation
          </button>
        )}
      </div>

      <div className="chat-history">
        {history.length === 0 && (
          <div className="chat-empty">
            <p>Ask a question about your data — or try one of these:</p>
            <div className="suggestion-chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {history.map((entry, i) => (
          <Exchange key={i} entry={entry} />
        ))}
        {loading && (
          <div className="chat-exchange">
            <div className="chat-question">
              <span className="chat-avatar user">Y</span>
              {question || "…"}
            </div>
            <div className="chat-answer">
              <span className="chat-avatar agent">AI</span>
              <div className="chat-thinking">
                <span className="spinner" /> thinking…
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="chat-input-row">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={history.length > 0 ? "Ask a follow-up…" : "Ask a question about your data…"}
          rows={2}
        />
        <button className="run-btn" onClick={handleAsk} disabled={loading}>
          {loading ? <span className="spinner" /> : "Ask"}
        </button>
      </div>
    </div>
  );
}
