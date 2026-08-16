import { useState } from "react";
import { Dashboard } from "./views/Dashboard.jsx";
import { Discover } from "./views/Discover.jsx";
import { Apply } from "./views/Apply.jsx";
import { Approvals } from "./views/Approvals.jsx";
import { Health } from "./views/Health.jsx";
import { Controls } from "./views/Controls.jsx";
import { Settings } from "./views/Settings.jsx";

const NAV = [
  ["dashboard", "Dashboard"],
  ["discover", "Discover"],
  ["apply", "Apply"],
  ["approvals", "Approvals"],
  ["health", "Health"],
  ["controls", "Controls"],
  ["settings", "Settings"],
];

export function App({ rpc }) {
  const [view, setView] = useState("dashboard");
  const [selectedJob, setSelectedJob] = useState(null);

  const navigate = (next, job) => {
    setSelectedJob(job || null);
    setView(next);
  };

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">JoBot Desktop</span>
        <nav className="nav">
          {NAV.map(([key, label]) => (
            <button
              key={key}
              className={view === key ? "nav-item active" : "nav-item"}
              onClick={() => navigate(key)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main className="content">
        {rpc === null ? (
          <p className="muted">
            Sidecar unavailable — install JoBot and ensure <code>jobot</code> is
            on PATH.
          </p>
        ) : view === "dashboard" ? (
          <Dashboard rpc={rpc} />
        ) : view === "discover" ? (
          <Discover rpc={rpc} onApply={(job) => navigate("apply", job)} />
        ) : view === "apply" ? (
          <Apply rpc={rpc} job={selectedJob} />
        ) : view === "approvals" ? (
          <Approvals rpc={rpc} />
        ) : view === "health" ? (
          <Health rpc={rpc} />
        ) : view === "controls" ? (
          <Controls rpc={rpc} />
        ) : (
          <Settings rpc={rpc} />
        )}
      </main>
    </div>
  );
}
