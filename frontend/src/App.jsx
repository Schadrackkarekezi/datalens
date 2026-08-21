import { useState } from "react";
import SchemaBrowser from "./components/SchemaBrowser";
import QueryEditor from "./components/QueryEditor";
import ResultsTable from "./components/ResultsTable";
import { runQuery } from "./api";

export default function App() {
  const [sql, setSql] = useState("SELECT * FROM deals LIMIT 10");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runQuery(sql);
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <SchemaBrowser
        onPickTable={(name) => setSql(`SELECT * FROM ${name} LIMIT 10`)}
      />
      <main>
        <h1>DataLens</h1>
        <QueryEditor sql={sql} setSql={setSql} onRun={handleRun} loading={loading} />
        {error && <div className="error-banner">{error}</div>}
        <ResultsTable result={result} />
      </main>
    </div>
  );
}
