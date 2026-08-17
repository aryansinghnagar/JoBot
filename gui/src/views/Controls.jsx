import { useState } from "react";
import { useAsync } from "../lib/useAsync.js";

const SCHEDULE_PRESETS = [
  { label: "Weekdays at 9:00 AM", cron: "0 9 * * 1-5" },
  { label: "Every 2 hours (9 AM - 5 PM weekdays)", cron: "0 9-17/2 * * 1-5" },
  { label: "Once daily at 10:00 AM", cron: "0 10 * * *" },
  { label: "Weekly on Monday at 9:00 AM", cron: "0 9 * * 1" },
  { label: "Custom Schedule...", cron: "custom" },
];

export function Controls({ rpc }) {
  const { loading, data, error, refresh } = useAsync(
    () => rpc.campaignStatus(),
    [rpc],
  );
  const [busy, setBusy] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(SCHEDULE_PRESETS[0].cron);
  const [customCron, setCustomCron] = useState("0 9 * * 1-5");
  const [command, setCommand] = useState("run");
  const [message, setMessage] = useState(null);

  const effectiveCron = selectedPreset === "custom" ? customCron : selectedPreset;

  const act = async (fn, ok) => {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
      setMessage(ok);
      refresh();
    } catch (err) {
      setMessage(String((err && err.message) || err));
    } finally {
      setBusy(false);
    }
  };

  const addSchedule = (e) => {
    e.preventDefault();
    act(async () => {
      await rpc.scheduleAdd(effectiveCron, command);
    }, "Schedule added successfully.");
  };

  const removeSchedule = (id) => {
    if (!window.confirm("Are you sure you want to remove this scheduled campaign run?")) {
      return;
    }
    act(async () => {
      await rpc.scheduleRemove(id);
    }, "Schedule removed.");
  };

  return (
    <section>
      <h1>Campaign Controls</h1>
      <p className="muted">
        Manage automated recurring discovery and application campaign runs.
      </p>

      {message && <p className="card success-box">{message}</p>}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>Campaign Runner</h2>
        <p>
          Status: <strong>{data?.runner?.status || "IDLE"}</strong>
        </p>
        <div className="row" style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
          <button
            className="btn btn-secondary"
            onClick={() => act(rpc.pause, "Campaign paused.")}
            disabled={busy}
          >
            Pause Campaign
          </button>
          <button
            className="btn btn-primary"
            onClick={() => act(rpc.resume, "Campaign resumed.")}
            disabled={busy}
          >
            Resume Campaign
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Active Schedules</h2>
        {loading && <p className="muted">Loading schedules…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && data && (
          <>
            {data.schedules.length === 0 ? (
              <p className="muted">No scheduled jobs configured. Add a schedule below.</p>
            ) : (
              <table style={{ width: "100%", marginBottom: "1.5rem" }}>
                <thead>
                  <tr>
                    <th>Schedule ID</th>
                    <th>Schedule Rule</th>
                    <th>Action</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.schedules.map((s) => (
                    <tr key={s.schedule_id}>
                      <td><code>{s.schedule_id}</code></td>
                      <td><code>{s.cron}</code></td>
                      <td>{s.command === "run" ? "Discover & Match" : s.command}</td>
                      <td>
                        <span className={`badge ${s.active ? "badge-success" : "badge-secondary"}`}>
                          {s.active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => removeSchedule(s.schedule_id)}
                          disabled={busy}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <h3 style={{ marginTop: "1rem" }}>Add New Schedule</h3>
            <form className="form" onSubmit={addSchedule}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
                <label>
                  Frequency Preset
                  <select
                    value={selectedPreset}
                    onChange={(e) => setSelectedPreset(e.target.value)}
                  >
                    {SCHEDULE_PRESETS.map((p) => (
                      <option key={p.cron} value={p.cron}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Action Command
                  <select
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                  >
                    <option value="run">Run discovery and match pipeline</option>
                    <option value="scrape">Scrape new postings only</option>
                  </select>
                </label>
              </div>

              {selectedPreset === "custom" && (
                <label style={{ marginBottom: "1rem" }}>
                  Custom Cron Expression (e.g. <code>0 9 * * 1-5</code>)
                  <input
                    value={customCron}
                    onChange={(e) => setCustomCron(e.target.value)}
                    placeholder="0 9 * * 1-5"
                  />
                </label>
              )}

              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "Saving..." : "Add Schedule"}
              </button>
            </form>
          </>
        )}
      </div>
    </section>
  );
}
