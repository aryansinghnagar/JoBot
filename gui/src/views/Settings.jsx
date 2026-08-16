import { useAsync } from "../lib/useAsync.js";

export function Settings({ rpc }) {
  const doctor = useAsync(() => rpc.doctor(), [rpc]);
  const config = useAsync(() => rpc.configShow(), [rpc]);
  const digest = useAsync(() => rpc.digest(7), [rpc]);
  const traces = useAsync(() => rpc.traces(), [rpc]);

  return (
    <section>
      <h1>Settings &amp; Diagnostics</h1>

      <div className="card">
        <h2>Doctor</h2>
        {doctor.loading ? (
          <p className="muted">Running diagnostics…</p>
        ) : doctor.error ? (
          <p className="error">{doctor.error}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Check</th>
                <th>Status</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {doctor.data.checks.map((c, i) => (
                <tr key={i}>
                  <td>{c.label}</td>
                  <td>
                    {c.warn ? (c.ok ? "PASS" : "WARN") : c.ok ? "PASS" : "FAIL"}
                  </td>
                  <td className="muted">{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Configuration</h2>
        {config.loading ? (
          <p className="muted">Loading…</p>
        ) : config.error ? (
          <p className="error">{config.error}</p>
        ) : (
          <ul className="counts">
            {Object.entries(config.data.config || {}).map(([k, v]) => (
              <li key={k}>
                <span>{k}</span>
                <strong>{v}</strong>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Weekly Digest (preview)</h2>
        {digest.loading ? (
          <p className="muted">Generating…</p>
        ) : digest.error ? (
          <p className="error">{digest.error}</p>
        ) : (
          <>
            <p>
              <strong>{digest.data.subject}</strong>
            </p>
            <pre className="digest">{digest.data.text}</pre>
          </>
        )}
      </div>

      <div className="card">
        <h2>Traces</h2>
        {traces.loading ? (
          <p className="muted">Loading…</p>
        ) : traces.error ? (
          <p className="error">{traces.error}</p>
        ) : traces.data.runs.length === 0 ? (
          <p className="muted">No trace runs recorded.</p>
        ) : (
          <ul className="counts">
            {traces.data.runs.map((run) => (
              <li key={run.run_id}>
                <span>{run.run_id}</span>
                <strong>{run.span_count} spans</strong>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
