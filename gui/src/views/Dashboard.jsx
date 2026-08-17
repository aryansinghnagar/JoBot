import { useState } from "react";
import { useAsync } from "../lib/useAsync.js";

const KANBAN_STAGES = [
  { id: "discovered", title: "Discovered", color: "#89b4fa" },
  { id: "pending_approval", title: "In Review", color: "#f9e2af" },
  { id: "submitted", title: "Applied", color: "#a6e3a1" },
  { id: "interviewing", title: "Interviewing", color: "#cba6f7" },
  { id: "offered", title: "Offered 🎉", color: "#94e2d5" },
];

export function Dashboard({ rpc }) {
  const { loading, data, error, reload } = useAsync(
    () => rpc.trackerStats(),
    [rpc],
  );
  const [viewMode, setViewMode] = useState("kanban"); // "kanban" | "table"

  return (
    <section>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h1>Application Cockpit</h1>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            className={`btn ${viewMode === "kanban" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setViewMode("kanban")}
            style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
          >
            📋 Kanban Board
          </button>
          <button
            className={`btn ${viewMode === "table" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setViewMode("table")}
            style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}
          >
            📄 Table View
          </button>
        </div>
      </div>

      {loading && <p className="muted">Loading tracker stats…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && data && (
        <DashboardBody data={data} viewMode={viewMode} onRefresh={reload} />
      )}
    </section>
  );
}

function DashboardBody({ data, viewMode }) {
  const funnel = data.funnel || {};
  const counts = data.status_counts || {};
  const recent = data.recent || [];

  const totalApps = funnel.total || 0;
  const timeSavedHours = (totalApps * 0.25).toFixed(1); // 15 mins saved per application

  const cards = [
    ["Total Tracked", totalApps],
    ["Pending Review", funnel.pending_approval || 0],
    ["Submitted", funnel.submitted || 0],
    ["Time Saved", `${timeSavedHours} hrs`],
  ];

  return (
    <>
      <div className="grid" style={{ marginBottom: "1.5rem" }}>
        {cards.map(([label, value]) => (
          <div className="card" key={label}>
            <div
              className="num"
              style={{ color: label === "Time Saved" ? "#a6e3a1" : undefined }}
            >
              {value}
            </div>
            <div className="label">{label}</div>
          </div>
        ))}
      </div>

      {viewMode === "kanban" ? (
        <KanbanView recent={recent} counts={counts} />
      ) : (
        <TableView recent={recent} counts={counts} />
      )}
    </>
  );
}

function KanbanView({ recent }) {
  // Map recent applications into Kanban columns
  const getStage = (status) => {
    const s = String(status || "").toLowerCase();
    if (s.includes("review") || s.includes("pending"))
      return "pending_approval";
    if (
      s.includes("submit") ||
      s.includes("verified") ||
      s.includes("complete")
    )
      return "submitted";
    if (s.includes("interview")) return "interviewing";
    if (s.includes("offer")) return "offered";
    return "discovered";
  };

  const columns = {
    discovered: [],
    pending_approval: [],
    submitted: [],
    interviewing: [],
    offered: [],
  };

  recent.forEach((item) => {
    const stage = getStage(item.status);
    if (columns[stage]) {
      columns[stage].push(item);
    } else {
      columns.discovered.push(item);
    }
  });

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "1rem",
        alignItems: "start",
        marginTop: "1rem",
      }}
    >
      {KANBAN_STAGES.map((stage) => {
        const items = columns[stage.id] || [];
        return (
          <div
            key={stage.id}
            style={{
              background: "#181825",
              borderRadius: "8px",
              border: "1px solid #313244",
              padding: "0.75rem",
              minHeight: "320px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "0.75rem",
                borderBottom: `2px solid ${stage.color}`,
                paddingBottom: "0.4rem",
              }}
            >
              <strong style={{ fontSize: "0.9rem", color: stage.color }}>
                {stage.title}
              </strong>
              <span
                style={{
                  background: "#313244",
                  color: "#cdd6f4",
                  fontSize: "0.75rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "10px",
                }}
              >
                {items.length}
              </span>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.6rem",
              }}
            >
              {items.map((app, idx) => (
                <div
                  key={idx}
                  style={{
                    background: "#1e1e2e",
                    padding: "0.75rem",
                    borderRadius: "6px",
                    border: "1px solid #313244",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                  }}
                >
                  <strong
                    style={{
                      fontSize: "0.85rem",
                      display: "block",
                      color: "#cdd6f4",
                    }}
                  >
                    {app.title || app.job_title || "Untitled Role"}
                  </strong>
                  <span style={{ fontSize: "0.8rem", color: "#a6adc8" }}>
                    {app.company || app.company_name || "Unknown Company"}
                  </span>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginTop: "0.5rem",
                      fontSize: "0.7rem",
                    }}
                  >
                    <span
                      style={{
                        background: "#313244",
                        padding: "0.15rem 0.4rem",
                        borderRadius: "4px",
                        textTransform: "uppercase",
                      }}
                    >
                      {app.site || "custom"}
                    </span>
                    <span style={{ color: "#a6e3a1" }}>{app.status}</span>
                  </div>
                </div>
              ))}
              {items.length === 0 && (
                <p
                  className="muted"
                  style={{
                    fontSize: "0.8rem",
                    textAlign: "center",
                    marginTop: "2rem",
                  }}
                >
                  No applications
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TableView({ recent, counts }) {
  return (
    <>
      <h2>Status Distribution</h2>
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        {Object.entries(counts).length === 0 ? (
          <p className="muted">No applications tracked yet.</p>
        ) : (
          <ul className="counts">
            {Object.entries(counts).map(([status, n]) => (
              <li key={status}>
                <span className={`status status-${status}`}>{status}</span>
                <strong>{n}</strong>
              </li>
            ))}
          </ul>
        )}
      </div>

      <h2>Recent Applications</h2>
      <table>
        <thead>
          <tr>
            <th>Site</th>
            <th>Title</th>
            <th>Company</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((row, i) => (
            <tr key={i}>
              <td>{row.site}</td>
              <td>{row.title || row.job_title}</td>
              <td>{row.company || row.company_name}</td>
              <td>{row.status}</td>
            </tr>
          ))}
          {recent.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                No recent activity.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}
