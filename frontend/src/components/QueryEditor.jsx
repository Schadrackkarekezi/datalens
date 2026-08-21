import { useEffect } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { sql as sqlLang } from "@codemirror/lang-sql";

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
      <div className="code-frame">
        <CodeMirror
          value={sql}
          height="140px"
          theme="dark"
          extensions={[sqlLang()]}
          basicSetup={{ foldGutter: false }}
          onChange={setSql}
        />
      </div>
      <button className="run-btn" onClick={onRun} disabled={loading}>
        {loading ? <span className="spinner" /> : "Run"}
        <span className="shortcut">⌘/Ctrl + Enter</span>
      </button>
    </div>
  );
}
