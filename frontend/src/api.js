const BASE_URL = "http://127.0.0.1:8000";

// Only sent if VITE_API_KEY is set at build time — auth is opt-in server-side
// too (backend/auth.py), so local dev with no key configured needs no header.
const API_KEY = import.meta.env.VITE_API_KEY;

function headers(extra = {}) {
  return API_KEY ? { ...extra, "X-API-Key": API_KEY } : extra;
}

export async function getSchema() {
  const res = await fetch(`${BASE_URL}/schema`);
  if (!res.ok) throw new Error(`Failed to load schema (${res.status})`);
  return res.json();
}

export async function runQuery(sql) {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ sql }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Query failed (${res.status})`);
  return data;
}

export async function askQuestion(question, conversationId) {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Ask failed (${res.status})`);
  return data;
}

export async function clearConversation(conversationId) {
  await fetch(`${BASE_URL}/conversations/${conversationId}`, {
    method: "DELETE",
    headers: headers(),
  });
}

export async function getLogs(limit = 50) {
  const res = await fetch(`${BASE_URL}/logs?limit=${limit}`, { headers: headers() });
  if (!res.ok) throw new Error(`Failed to load logs (${res.status})`);
  return res.json();
}
