import { useEffect, useState } from "react";
import { getSchema } from "../api";

export default function SchemaBrowser({ onPickTable }) {
  const [tables, setTables] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSchema()
      .then((data) => setTables(data.tables))
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="schema-browser error">{error}</div>;

  return (
    <div className="schema-browser">
      <h2>Schema</h2>
      {tables.map((table) => (
        <div key={table.name} className="schema-table">
          <button
            className="schema-table-name"
            onClick={() => onPickTable(table.name)}
          >
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
    </div>
  );
}
