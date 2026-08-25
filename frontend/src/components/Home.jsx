import { useEffect, useState } from "react";
import { runQuery } from "../api";
import {
  SendIcon,
  ArrowRightIcon,
  DatabaseIcon,
  CheckCircleIcon,
  TargetIcon,
  CoinIcon,
  TerminalIcon,
  GraphIcon,
} from "./Icons";

const SUGGESTIONS = [
  "Which accounts have capacity contracts marked at_risk?",
  "Which reps logged the most POCs on deals for the Data Sharing workload?",
  "What's the total committed amount across active capacity contracts, by workload?",
];

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

// A snapshot query per tile — each one is a plain read-only SELECT run
// through the same safety-guarded /query endpoint the SQL editor uses, not
// a separate stats API. If a tile is wrong, it's wrong for the same reason
// a query editor result would be wrong — one code path, not two.
const SNAPSHOT_QUERIES = [
  { label: "Accounts", sql: "SELECT COUNT(*) FROM accounts", icon: DatabaseIcon, tone: "neutral" },
  {
    label: "Active contracts",
    sql: "SELECT COUNT(*) FROM capacity_contracts WHERE status = 'active'",
    icon: CheckCircleIcon,
    tone: "good",
  },
  {
    label: "At-risk contracts",
    sql: "SELECT COUNT(*) FROM capacity_contracts WHERE status = 'at_risk'",
    icon: TargetIcon,
    tone: "warn",
  },
  {
    label: "Committed capacity",
    sql: "SELECT ROUND(SUM(committed_amount)) FROM capacity_contracts WHERE status = 'active'",
    format: (v) => `$${(Number(v) / 1_000_000).toFixed(1)}M`,
    icon: CoinIcon,
    tone: "neutral",
  },
];

const LINKS = [
  {
    label: "Query Editor",
    description: "Write raw SQL directly, same safety guard as the agent",
    icon: TerminalIcon,
    target: "query",
  },
  {
    label: "Knowledge Graph",
    description: "Explore the schema's real relationships, interactively",
    icon: GraphIcon,
    target: "graph",
  },
];

export default function Home({ onAsk }) {
  const [question, setQuestion] = useState("");
  const [snapshot, setSnapshot] = useState(null);
  const [snapshotError, setSnapshotError] = useState(null);

  useEffect(() => {
    Promise.all(SNAPSHOT_QUERIES.map((q) => runQuery(q.sql)))
      .then((results) => {
        setSnapshot(
          results.map((r, i) => {
            const raw = r.rows[0][0];
            const q = SNAPSHOT_QUERIES[i];
            return q.format ? q.format(raw) : raw;
          })
        );
      })
      .catch((err) => setSnapshotError(err.message));
  }, []);

  const submit = () => {
    if (!question.trim()) return;
    onAsk(question);
    setQuestion("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="home-view">
      <div className="home-hero">
        <h1>{greeting()}. What do you want to know about your GTM data?</h1>
        <p>
          Ask in plain English — deals, capacity contracts, consumption trends, POCs. DataLens
          figures out the join path and writes the SQL.
        </p>

        <div className="home-ask-box">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. Which accounts are under-consuming ahead of renewal?"
            rows={2}
          />
          <button className="home-ask-submit" onClick={submit} disabled={!question.trim()}>
            <SendIcon />
          </button>
        </div>

        <div className="home-suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="suggestion-chip" onClick={() => onAsk(s)}>
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="home-snapshot">
        <div className="home-snapshot-label">GTM snapshot</div>
        {snapshotError && <div className="error-banner">{snapshotError}</div>}
        <div className="home-snapshot-tiles">
          {SNAPSHOT_QUERIES.map((q, i) => (
            <div className="home-snapshot-tile" key={q.label}>
              <span className={`stat-icon tone-${q.tone}`}>
                <q.icon width={15} height={15} />
              </span>
              <div>
                <div className={`home-snapshot-value tone-${q.tone}`}>
                  {snapshot ? snapshot[i] : "…"}
                </div>
                <div className="home-snapshot-tile-label">{q.label}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="home-links">
        {LINKS.map((link) => (
          <button className="home-link-card" key={link.label} onClick={() => onAsk(null, link.target)}>
            <span className="stat-icon tone-accent">
              <link.icon width={16} height={16} />
            </span>
            <div>
              <strong>{link.label}</strong>
              <span>{link.description}</span>
            </div>
            <ArrowRightIcon className="home-link-arrow" />
          </button>
        ))}
      </div>
    </div>
  );
}
