import { useEffect, useState } from "react";
import { getLogs } from "../api";

export default function Dashboard({ active }) {
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!active) return;
    getLogs(50)
      .then((data) => setEntries(data.entries))
      .catch((err) => setError(err.message));
  }, [active]);

  if (error) return <div className="error-banner">{error}</div>;

  if (entries.length === 0) {
    return <div className="chat-empty">No /ask calls logged yet — try the Ask AI tab first.</div>;
  }

  const successCount = entries.filter((e) => e.success).length;
  const avgLatency = Math.round(
    entries.reduce((sum, e) => sum + e.total_latency_ms, 0) / entries.length
  );
  const maxLatency = Math.max(...entries.map((e) => e.total_latency_ms));
  const totalCost = entries.reduce((sum, e) => sum + (e.estimated_cost_usd || 0), 0);
  const sqlEntries = entries.filter((e) => e.response_type === "sql");
  const verifiedCount = sqlEntries.filter((e) => e.verified).length;
  const verifiedRate = sqlEntries.length > 0 ? Math.round((verifiedCount / sqlEntries.length) * 100) : null;

  return (
    <div className="dashboard">
      <div className="dashboard-stats">
        <div className="stat-tile">
          <div className="stat-value">{entries.length}</div>
          <div className="stat-label">Calls logged</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{Math.round((successCount / entries.length) * 100)}%</div>
          <div className="stat-label">Success rate</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{avgLatency} ms</div>
          <div className="stat-label">Avg latency</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">${totalCost.toFixed(4)}</div>
          <div className="stat-label">Est. total cost</div>
        </div>
        {verifiedRate !== null && (
          <div className="stat-tile">
            <div className="stat-value">{verifiedRate}%</div>
            <div className="stat-label">Verified hit rate ({verifiedCount}/{sqlEntries.length})</div>
          </div>
        )}
      </div>

      <div className="latency-chart">
        {entries
          .slice()
          .reverse()
          .map((e, i) => (
            <div
              key={i}
              className={`latency-bar ${e.success ? "" : "failed"}`}
              style={{ height: `${Math.max(4, (e.total_latency_ms / maxLatency) * 100)}%` }}
              title={`${e.question} — ${e.total_latency_ms}ms`}
            />
          ))}
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Question</th>
              <th>Status</th>
              <th>Source</th>
              <th>Attempts</th>
              <th>Rows</th>
              <th>Latency</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr key={i}>
                <td>{e.timestamp}</td>
                <td className="log-question">{e.question}</td>
                <td>
                  <span className={`status-pill ${e.success ? "ok" : "fail"}`}>
                    {e.success ? "success" : "failed"}
                  </span>
                </td>
                <td>
                  {e.response_type === "sql" ? (
                    <span className={`verified-badge ${e.verified ? "verified" : "generated"}`}>
                      {e.verified ? "✓ verified" : "⚡ generated"}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td>{e.attempts ?? "—"}</td>
                <td>{e.row_count ?? "—"}</td>
                <td>{e.total_latency_ms} ms</td>
                <td>{e.estimated_cost_usd != null ? `$${e.estimated_cost_usd.toFixed(5)}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
