import { useEffect, useState } from "react";
import { getSchema } from "../api";

export default function SchemaBrowser({ onPickTable, activeTable, onSchemaLoaded }) {
  const [tables, setTables] = useState([]);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    getSchema()
      .then((data) => {
        setTables(data.tables);
        onSchemaLoaded?.(true);
      })
      .catch((err) => {
        setError(err.message);
        onSchemaLoaded?.(false);
      });
  }, []);

  if (error) return <div className="schema-browser error">{error}</div>;

  const filtered = tables.filter((t) =>
    t.name.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="schema-browser">
      <h2>Schema</h2>
      <input
        className="schema-search"
        placeholder="Filter tables…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      {filtered.map((table) => (
        <div
          key={table.name}
          className={`schema-table${activeTable === table.name ? " active" : ""}`}
        >
          <button className="schema-table-name" onClick={() => onPickTable(table.name)}>
            {table.name}
          </button>
          <ul>
            {table.columns.map((col) => (
              <li key={col.name}>
                <span>{col.name}</span>
                <span className="col-type">{col.type}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {tables.length > 0 && filtered.length === 0 && (
        <div className="schema-empty">No matching tables</div>
      )}
    </div>
  );
}
