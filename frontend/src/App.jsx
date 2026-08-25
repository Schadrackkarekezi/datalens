import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import Home from "./components/Home";
import DataCatalog from "./components/DataCatalog";
import Upload from "./components/Upload";
import QueryEditor from "./components/QueryEditor";
import QueryHistory from "./components/QueryHistory";
import ResultsTable from "./components/ResultsTable";
import ChatPanel from "./components/ChatPanel";
import Dashboard from "./components/Dashboard";
import GraphViewer from "./components/GraphViewer";
import { runQuery } from "./api";

const HISTORY_KEY = "datalens_query_history";

const PAGE_TITLES = {
  home: "Home",
  ask: "Ask AI",
  catalog: "Data Catalog",
  upload: "Upload",
  query: "Query Editor",
  graph: "Knowledge Graph",
  logs: "Observability",
};

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
  const [mode, setMode] = useState("home");
  const [graphHighlight, setGraphHighlight] = useState(null);
  const [pendingQuestion, setPendingQuestion] = useState(null);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }, [history]);

  const runSql = useCallback(async (queryText) => {
    setLoading(true);
    setError(null);
    try {
      const data = await runQuery(queryText);
      setResult(data);
      setHistory((prev) => {
        const entry = { sql: queryText, time: new Date().toLocaleTimeString() };
        return [entry, ...prev.filter((h) => h.sql !== queryText)].slice(0, 20);
      });
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRun = useCallback(() => runSql(sql), [sql, runSql]);

  // Clicking a table in the catalog previews it immediately — the whole
  // point is "click a table, see its data," not "click a table, then
  // remember to also press Run."
  const handlePickTable = (name) => {
    const query = `SELECT * FROM ${name} LIMIT 50`;
    setActiveTable(name);
    setSql(query);
    setMode("query");
    runSql(query);
  };

  const handleViewOnGraph = (entities) => {
    setGraphHighlight({ entities, onClear: () => setGraphHighlight(null) });
    setMode("graph");
  };

  // Home's entry points funnel through here — either a question (goes to
  // the one Ask AI conversation) or a direct link to another page.
  const handleHomeAsk = (question, targetMode) => {
    if (question) {
      setPendingQuestion(question);
      setMode("ask");
    } else if (targetMode) {
      setMode(targetMode);
    }
  };

  return (
    <div className="app">
      <Sidebar
        mode={mode}
        onModeChange={setMode}
        onPickTable={handlePickTable}
        activeTable={activeTable}
        onSchemaLoaded={setConnected}
        connected={connected}
      />
      <div className="main-column">
        <div className="content-topbar">
          <h1>{PAGE_TITLES[mode]}</h1>
          {mode === "query" && (
            <QueryHistory history={history} onSelect={setSql} onClear={() => setHistory([])} />
          )}
        </div>

        <main>
          {/* All panels stay mounted so switching pages never loses state
              (query history, the active conversation, dashboard scroll) —
              only visibility toggles. */}
          <div style={{ display: mode === "home" ? "block" : "none" }}>
            <Home onAsk={handleHomeAsk} />
          </div>

          <div style={{ display: mode === "catalog" ? "block" : "none" }}>
            <DataCatalog onPreview={handlePickTable} />
          </div>

          <div style={{ display: mode === "upload" ? "block" : "none" }}>
            <Upload />
          </div>

          <div style={{ display: mode === "query" ? "block" : "none" }}>
            <QueryEditor sql={sql} setSql={setSql} onRun={handleRun} loading={loading} />
            {error && <div className="error-banner">{error}</div>}
            <ResultsTable result={result} loading={loading} />
          </div>

          <div style={{ display: mode === "ask" ? "block" : "none" }}>
            <ChatPanel
              onViewOnGraph={handleViewOnGraph}
              pendingQuestion={pendingQuestion}
              onConsumePending={() => setPendingQuestion(null)}
            />
          </div>

          <div style={{ display: mode === "graph" ? "block" : "none" }}>
            <GraphViewer highlight={graphHighlight} />
          </div>

          <div style={{ display: mode === "logs" ? "block" : "none" }}>
            <Dashboard active={mode === "logs"} onViewOnGraph={handleViewOnGraph} />
          </div>
        </main>
      </div>
    </div>
  );
}
