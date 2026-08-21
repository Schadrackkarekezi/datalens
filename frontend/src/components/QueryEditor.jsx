import { useState, useEffect } from "react";

export default function QueryEditor({ sql, setSql, onRun, loading }) {
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") onRun();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onRun]);

  return (
    <div className="query-editor">
      <textarea
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        placeholder="SELECT * FROM deals LIMIT 10"
        rows={6}
      />
      <button onClick={onRun} disabled={loading}>
        {loading ? "Running..." : "Run (⌘/Ctrl+Enter)"}
      </button>
    </div>
  );
}
