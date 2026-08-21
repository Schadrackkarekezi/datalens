export default function ResultsTable({ result }) {
  if (!result) return null;

  const { columns, rows, row_count, execution_time_ms } = result;

  return (
    <div className="results-table">
      <div className="results-meta">
        {row_count} rows · {execution_time_ms} ms
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>{cell === null ? "NULL" : String(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
