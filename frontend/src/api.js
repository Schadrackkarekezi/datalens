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

export async function getGraph() {
  const res = await fetch(`${BASE_URL}/graph`);
  if (!res.ok) throw new Error(`Failed to load graph (${res.status})`);
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

// SSE version of askQuestion — only "unstructured"/"hybrid" answers ever
// send "start"/"delta" events (that's the one call in the pipeline that
// writes free-form prose instead of strict JSON, so it's the only one
// that can stream meaningfully); "sql"/"chat" turns go straight to
// onComplete, same as the non-streaming endpoint. A backend "error" event
// is thrown here rather than passed to a callback, so callers can handle
// it with the same try/catch they'd use for a network failure.
export async function askQuestionStream(question, conversationId, { onStart, onDelta, onSynthError, onComplete }) {
  const res = await fetch(`${BASE_URL}/ask/stream`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!res.ok || !res.body) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* body wasn't JSON — fall through to the generic message below */
    }
    throw new Error(detail || `Ask failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const dataLine = rawEvent.split("\n").find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      const event = JSON.parse(dataLine.slice(6));

      if (event.type === "start") onStart?.(event.data);
      else if (event.type === "delta") onDelta?.(event.text);
      else if (event.type === "synth_error") onSynthError?.(event.text);
      else if (event.type === "complete") onComplete?.(event.data);
      else if (event.type === "error") throw new Error(event.message);
    }
  }
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

export async function uploadAccountNote(accountId, content, authorRole) {
  const res = await fetch(`${BASE_URL}/upload/account-note`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ account_id: accountId, content, author_role: authorRole }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Upload failed (${res.status})`);
  return data;
}

export async function uploadEnablementContent(title, category, content) {
  const res = await fetch(`${BASE_URL}/upload/enablement-content`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ title, category, content }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Upload failed (${res.status})`);
  return data;
}
