const BASE_URL = "http://127.0.0.1:8000";

export async function getSchema() {
  const res = await fetch(`${BASE_URL}/schema`);
  if (!res.ok) throw new Error(`Failed to load schema (${res.status})`);
  return res.json();
}

export async function runQuery(sql) {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Query failed (${res.status})`);
  return data;
}
