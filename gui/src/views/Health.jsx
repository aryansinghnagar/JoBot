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
    </section>
  );
}
