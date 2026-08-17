import { useEffect, useState } from "react";
import { Dashboard } from "./views/Dashboard.jsx";
import { Discover } from "./views/Discover.jsx";
import { Apply } from "./views/Apply.jsx";
import { Approvals } from "./views/Approvals.jsx";
import { Health } from "./views/Health.jsx";
import { Controls } from "./views/Controls.jsx";
import { Settings } from "./views/Settings.jsx";
import { Help } from "./views/Help.jsx";
import { Onboarding } from "./views/Onboarding.jsx";
import { Profile } from "./views/Profile.jsx";

const NAV = [
  ["dashboard", "Dashboard"],
  ["discover", "Discover"],
  ["apply", "Apply"],
  ["approvals", "Approvals"],
  ["profile", "Profile & Truth"],
  ["health", "Health"],
  ["controls", "Controls"],
  ["settings", "Settings"],
  ["help", "Help & Guide"],
];

export function App({ rpc }) {
  const [view, setView] = useState("dashboard");
  const [selectedJob, setSelectedJob] = useState(null);

  useEffect(() => {
    if (!rpc) return;
    rpc.profileInfo().catch(() => {
      // If profile is missing, automatically show the setup wizard
      setView("onboarding");
    });
  }, [rpc]);

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
          <div
            style={{
              textAlign: "center",
              padding: "4rem 1rem",
              maxWidth: "500px",
              margin: "0 auto",
            }}
          >
            <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚡</div>
            <h2>Connecting to JoBot Engine</h2>
            <p className="muted" style={{ marginTop: "0.5rem" }}>
              Initializing local privacy-preserving database and encrypted
              vault...
            </p>
            <div
              style={{
                marginTop: "1.5rem",
                background: "#181825",
                padding: "1rem",
                borderRadius: "8px",
                border: "1px solid #313244",
                fontSize: "0.85rem",
                color: "#a6adc8",
              }}
            >
              💡 If this takes longer than a few seconds, please ensure JoBot
              Desktop is installed and relaunch the application.
            </div>
          </div>
        ) : view === "onboarding" ? (
          <Onboarding rpc={rpc} onComplete={() => navigate("dashboard")} />
        ) : view === "dashboard" ? (
          <Dashboard rpc={rpc} />
        ) : view === "discover" ? (
          <Discover rpc={rpc} onApply={(job) => navigate("apply", job)} />
        ) : view === "apply" ? (
          <Apply rpc={rpc} job={selectedJob} />
        ) : view === "approvals" ? (
          <Approvals rpc={rpc} />
        ) : view === "profile" ? (
          <Profile rpc={rpc} />
        ) : view === "health" ? (
          <Health rpc={rpc} />
        ) : view === "controls" ? (
          <Controls rpc={rpc} />
        ) : view === "settings" ? (
          <Settings rpc={rpc} />
        ) : (
          <Help />
        )}
      </main>
    </div>
  );
}
