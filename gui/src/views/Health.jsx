import { useEffect, useState } from "react";

export function Health({ rpc }) {
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadHealth = async () => {
    setLoading(true);
    try {
      const res = await rpc.call("site_health", {});
      setSites(res?.sites || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <section className="view">
      <h2>Portal & ATS Site Health</h2>
      <p className="muted">
        Real-time availability, success rates, latency, and circuit breaker
        status across all supported job sites.
      </p>

      {loading ? (
        <p className="muted">Loading health metrics...</p>
      ) : (
        <div className="card">
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              textAlign: "left",
            }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid #333" }}>
                <th style={{ padding: "0.5rem" }}>Portal</th>
                <th style={{ padding: "0.5rem" }}>Status</th>
                <th style={{ padding: "0.5rem" }}>Total Requests</th>
                <th style={{ padding: "0.5rem" }}>Success Rate</th>
                <th style={{ padding: "0.5rem" }}>Consecutive Fails</th>
                <th style={{ padding: "0.5rem" }}>Last Error</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((s) => (
                <tr key={s.site} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: "0.5rem", fontWeight: "bold" }}>
                    {s.site}
                  </td>
                  <td style={{ padding: "0.5rem" }}>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                        fontWeight: "bold",
                        background:
                          s.status === "HEALTHY"
                            ? "#1e4620"
                            : s.status === "DEGRADED"
                              ? "#664d03"
                              : "#5c1d1d",
                        color:
                          s.status === "HEALTHY"
                            ? "#75b798"
                            : s.status === "DEGRADED"
                              ? "#ffda6a"
                              : "#ea868f",
                      }}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td style={{ padding: "0.5rem" }}>
                    {s.success_count + s.failure_count}
                  </td>
                  <td style={{ padding: "0.5rem" }}>
                    {(s.success_rate * 100).toFixed(1)}%
                  </td>
                  <td style={{ padding: "0.5rem" }}>
                    {s.consecutive_failures}
                  </td>
                  <td
                    style={{
                      padding: "0.5rem",
                      color: "#888",
                      fontSize: "0.85rem",
                    }}
                  >
                    {s.last_error || "None"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BrowserProvisionCard rpc={rpc} />
    </section>
  );
}

function BrowserProvisionCard({ rpc }) {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);
  const [msg, setMsg] = useState(null);

  const handleInstall = async () => {
    setBusy(true);
    setMsg("Downloading and verifying stealth Chromium browser engine...");
    setStatus(null);
    try {
      const res = await rpc.setupBrowser();
      if (res.status === "installed") {
        setStatus("success");
        setMsg(
          "✓ Chromium browser engine is installed and ready for live automation!",
        );
      } else {
        setStatus("error");
        setMsg(res.message || "Failed to download browser engine");
      }
    } catch (err) {
      setStatus("error");
      setMsg(
        err?.user_message || err?.message || "Failed to provision browser",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: "1.5rem" }}>
      <h2>Stealth Browser Automation Engine</h2>
      <p className="muted">
        Required for automated application submissions on LinkedIn, Workday, and
        Naukri.
      </p>
      <div style={{ marginTop: "1rem" }}>
        <button
          className="btn btn-secondary"
          onClick={handleInstall}
          disabled={busy}
          style={{ fontSize: "0.85rem" }}
        >
          {busy
            ? "Downloading Chromium Engine (1-2 mins)…"
            : "⚡ Verify / Install Browser Engine (1-Click)"}
        </button>
        {msg && (
          <p
            style={{
              marginTop: "0.5rem",
              fontSize: "0.85rem",
              color:
                status === "success"
                  ? "#10b981"
                  : status === "error"
                    ? "#ea868f"
                    : "#f9e2af",
            }}
          >
            {msg}
          </p>
        )}
      </div>
    </div>
  );
}
