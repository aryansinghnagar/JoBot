import { useState } from "react";
import { useAsync } from "../lib/useAsync.js";

export function Controls({ rpc }) {
  const { loading, data, error, refresh } = useAsync(
    () => rpc.campaignStatus(),
    [rpc],
  );
  const [busy, setBusy] = useState(false);
  const [cron, setCron] = useState("0 9 * * 1-5");
  const [command, setCommand] = useState("run");
  const [message, setMessage] = useState(null);

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
      await rpc.scheduleAdd(cron, command);
    }, "Schedule added.");
  };

  const removeSchedule = (id) => {
    act(async () => {
      await rpc.scheduleRemove(id);
    }, "Schedule removed.");
  };

  return (
    <section>
      <h1>Campaign Controls</h1>
      {message && <p className="muted">{message}</p>}

      <div className="card">
        <h2>Runner</h2>
        <p>
          Status: <strong>{data?.runner?.status || "UNKNOWN"}</strong>
        </p>
        <div className="row">
          <button onClick={() => act(rpc.pause, "Paused.")} disabled={busy}>
            Pause
          </button>
          <button onClick={() => act(rpc.resume, "Resumed.")} disabled={busy}>
            Resume
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Schedules</h2>
        {loading && <p className="muted">Loading schedules…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && data && (
          <>
            {data.schedules.length === 0 ? (
              <p className="muted">No schedules configured.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Cron</th>
                    <th>Command</th>
                    <th>Active</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.schedules.map((s) => (
                    <tr key={s.schedule_id}>
                      <td>{s.schedule_id}</td>
                      <td>{s.cron}</td>
                      <td>{s.command}</td>
                      <td>{String(s.active)}</td>
                      <td>
                        <button
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
            <form className="form row" onSubmit={addSchedule}>
              <input
                value={cron}
                onChange={(e) => setCron(e.target.value)}
                title="Cron expression"
              />
              <input
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                title="Command"
              />
              <button type="submit" disabled={busy}>
                Add schedule
              </button>
            </form>
          </>
        )}
      </div>
    </section>
  );
}
