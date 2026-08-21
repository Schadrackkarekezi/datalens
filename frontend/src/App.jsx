import { useCallback, useEffect, useState } from "react";
import Topbar from "./components/Topbar";
import SchemaBrowser from "./components/SchemaBrowser";
import QueryEditor from "./components/QueryEditor";
import QueryHistory from "./components/QueryHistory";
import ResultsTable from "./components/ResultsTable";
import ChatPanel from "./components/ChatPanel";
import Dashboard from "./components/Dashboard";
import { runQuery } from "./api";

const HISTORY_KEY = "datalens_query_history";

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch {
    return [];
  }
}

export default function App() {
  const [sql, setSql] = useState("SELECT * FROM deals LIMIT 10");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(null);
  const [activeTable, setActiveTable] = useState(null);
  const [history, setHistory] = useState(loadHistory);
  const [mode, setMode] = useState("query");

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }, [history]);

  const handleRun = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runQuery(sql);
      setResult(data);
      setHistory((prev) => {
        const entry = { sql, time: new Date().toLocaleTimeString() };
        return [entry, ...prev.filter((h) => h.sql !== sql)].slice(0, 20);
      });
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [sql]);

  const handlePickTable = (name) => {
    setActiveTable(name);
    setSql(`SELECT * FROM ${name} LIMIT 10`);
  };

  return (
    <div className="app">
      <Topbar connected={connected} />
      <div className="app-body">
        <SchemaBrowser
          onPickTable={handlePickTable}
          activeTable={activeTable}
          onSchemaLoaded={setConnected}
        />
        <main>
          <div className="toolbar">
            <div className="mode-tabs">
              <button className={mode === "query" ? "active" : ""} onClick={() => setMode("query")}>
                Query Editor
              </button>
              <button className={mode === "ask" ? "active" : ""} onClick={() => setMode("ask")}>
                Ask AI
              </button>
              <button className={mode === "logs" ? "active" : ""} onClick={() => setMode("logs")}>
                Observability
              </button>
            </div>
            {mode === "query" && (
              <QueryHistory history={history} onSelect={setSql} onClear={() => setHistory([])} />
            )}
          </div>

          {/* All three panels stay mounted so switching tabs never loses state
              (query history, the active conversation, dashboard scroll) — only
              visibility toggles. */}
          <div style={{ display: mode === "query" ? "block" : "none" }}>
            <QueryEditor sql={sql} setSql={setSql} onRun={handleRun} loading={loading} />
            {error && <div className="error-banner">{error}</div>}
            <ResultsTable result={result} loading={loading} />
          </div>

          <div style={{ display: mode === "ask" ? "block" : "none" }}>
            <ChatPanel />
          </div>

          <div style={{ display: mode === "logs" ? "block" : "none" }}>
            <Dashboard active={mode === "logs"} />
          </div>
        </main>
      </div>
    </div>
  );
}
