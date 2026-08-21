export default function Topbar({ connected }) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="logo-dot" />
        <span className="brand-name">DataLens</span>
        <span className="brand-sub">SQL Query Tool</span>
      </div>
      <div className="topbar-status">
        <span
          className={`status-dot ${
            connected === null ? "pending" : connected ? "online" : "offline"
          }`}
        />
        {connected === null ? "Connecting…" : connected ? "Connected" : "Disconnected"}
      </div>
    </header>
  );
}
