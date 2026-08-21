const STEP_META = {
  retrieve: { icon: "📚", label: "Retrieved business context" },
  graph_lookup: { icon: "🕸️", label: "Graph lookup" },
  respond: { icon: "⚙️", label: "Generate response" },
};

function describeStep(step) {
  if (step.step === "retrieve") {
    const terms = step.retrieved_terms || [];
    const history = step.history_turns_used || 0;
    const parts = [
      terms.length > 0 ? `matched: ${terms.join(", ")}` : "no matching business terms",
    ];
    if (history > 0) parts.push(`using ${history} prior turn${history > 1 ? "s" : ""} of context`);
    return parts.join(" · ");
  }

  if (step.step === "graph_lookup") {
    const entities = step.relevant_entities || [];
    const paths = step.join_paths || [];
    if (entities.length === 0) return "no relevant entities detected";
    if (paths.length === 0) return `entities: ${entities.join(", ")} (single table, no join needed)`;
    return `entities: ${entities.join(", ")} · ${paths.length} join path${paths.length > 1 ? "s" : ""} found`;
  }

  if (step.step === "respond") {
    if (step.status === "chat") return "replied conversationally, no query needed";
    if (step.status === "error") return `attempt ${step.attempt} failed: ${step.error} — retrying`;
    return `attempt ${step.attempt} · ${step.row_count} row${step.row_count === 1 ? "" : "s"} returned`;
  }

  return "";
}

function stepStatus(step) {
  if (step.step === "respond" && step.status === "error") return "warn";
  return "ok";
}

export default function ReasoningTrace({ trace }) {
  if (!trace || trace.length === 0) return null;

  return (
    <ol className="reasoning-trace">
      {trace.map((step, i) => {
        const meta = STEP_META[step.step] || { icon: "•", label: step.step };
        const status = stepStatus(step);
        return (
          <li key={i} className={`trace-step trace-${status}`}>
            <span className="trace-icon">{meta.icon}</span>
            <div className="trace-body">
              <div className="trace-label">
                {meta.label}
                <span className="trace-latency">{step.latency_ms ?? step.generate_latency_ms} ms</span>
              </div>
              <div className="trace-detail">{describeStep(step)}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
