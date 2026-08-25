import SchemaBrowser from "./SchemaBrowser";
import ThemeToggle from "./ThemeToggle";
import { HomeIcon, TerminalIcon, GraphIcon, ChartIcon, DatabaseIcon, UploadIcon } from "./Icons";

const NAV_ITEMS = [
  { id: "home", label: "Home", Icon: HomeIcon },
  { id: "catalog", label: "Data Catalog", Icon: DatabaseIcon },
  { id: "upload", label: "Upload", Icon: UploadIcon },
  { id: "query", label: "Query Editor", Icon: TerminalIcon },
  { id: "graph", label: "Graph", Icon: GraphIcon },
  { id: "logs", label: "Observability", Icon: ChartIcon },
];

export default function Sidebar({ mode, onModeChange, onPickTable, activeTable, onSchemaLoaded, connected }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="logo-mark">T</span>
        <div className="sidebar-brand-text">
          <span className="brand-name">Traceview</span>
          <span className="brand-sub">GTM Intelligence</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ id, label, Icon }) => {
          // "ask" has no nav entry of its own - it's only ever reached from
          // Home's ask box - so while a conversation is active, Home is
          // still the nav item that reads as "where you are."
          const isActive = mode === id || (id === "home" && mode === "ask");
          return (
            <button
              key={id}
              className={`sidebar-nav-item${isActive ? " active" : ""}`}
              onClick={() => onModeChange(id)}
            >
              <Icon className="sidebar-nav-icon" />
              {label}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-records">
        <SchemaBrowser
          onPickTable={onPickTable}
          activeTable={activeTable}
          onSchemaLoaded={onSchemaLoaded}
          onOpenCatalog={() => onModeChange("catalog")}
        />
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-footer-status">
          <span
            className={`status-dot ${connected === null ? "pending" : connected ? "online" : "offline"}`}
          />
          {connected === null ? "Connecting…" : connected ? "Connected" : "Disconnected"}
        </div>
        <ThemeToggle />
      </div>
    </aside>
  );
}
