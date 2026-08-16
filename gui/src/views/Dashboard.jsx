import { useAsync } from "../lib/useAsync.js";

export function Dashboard({ rpc }) {
  const { loading, data, error } = useAsync(() => rpc.trackerStats(), [rpc]);

  return (
    <section>
      <h1>Application Dashboard</h1>
      {loading && <p className="muted">Loading tracker stats…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && data && <DashboardBody data={data} />}
    </section>
  );
}

function DashboardBody({ data }) {
  const funnel = data.funnel || {};
  const counts = data.status_counts || {};
  const cards = [
    ["Total", funnel.total],
    ["Pending Approval", funnel.pending_approval],
    ["Submitted", funnel.submitted],
    ["Verified", funnel.verified],
  ];
  const recent = data.recent || [];

  return (
    <>
      <div className="grid">
        {cards.map(([label, value]) => (
          <div className="card" key={label}>
            <div className="num">{value ?? 0}</div>
            <div className="label">{label}</div>
          </div>
        ))}
      </div>

      <h2>By Status</h2>
      <div className="card">
        {Object.entries(counts).length === 0 ? (
          <p className="muted">No applications tracked yet.</p>
        ) : (
          <ul className="counts">
            {Object.entries(counts).map(([status, n]) => (
              <li key={status}>
                <span className="status status-{status}">{status}</span>
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
