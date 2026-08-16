import { useState } from "react";

const TEMPLATES = ["default", "modern", "classic"];
const TONES = ["classic", "concise", "technical", "warm", "assertive"];

export function Apply({ rpc, job }) {
  const [jobId, setJobId] = useState("");
  const [url, setUrl] = useState(job ? job.url : "");
  const [site, setSite] = useState(job ? job.site : "");
  const [dryRun, setDryRun] = useState(true);
  const [template, setTemplate] = useState("default");
  const [tone, setTone] = useState("classic");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const run = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    const params = {
      dry_run: dryRun,
      template,
      tone,
    };
    if (job) {
      params.job_id = job.job_id;
    } else if (jobId) {
      params.job_id = jobId;
    } else if (url) {
      params.url = url;
      if (site) params.site = site;
    } else {
      setError("Provide a saved job id or a posting URL.");
      setBusy(false);
      return;
    }
    try {
      const res = await rpc.apply(params);
      setResult(res);
    } catch (err) {
      setError(String((err && err.message) || err));
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!result || !result.application_id) return;
    setBusy(true);
    setError(null);
    try {
      const res = await rpc.approve(result.application_id);
      setResult(res);
    } catch (err) {
      setError(String((err && err.message) || err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h1>Apply</h1>
      {job ? (
        <div className="card">
          <strong>{job.title}</strong>
          <span className="muted">
            {" "}
            — {job.company} ({job.site})
          </span>
        </div>
      ) : (
        <p className="muted">
          Pick a job from Discover, or enter a saved job id / posting URL below.
        </p>
      )}

      <form className="form" onSubmit={run}>
        {!job && (
          <>
            <label>
              Saved job id
              <input value={jobId} onChange={(e) => setJobId(e.target.value)} />
            </label>
            <label>
              Job URL
              <input value={url} onChange={(e) => setUrl(e.target.value)} />
            </label>
            <label>
              Site (inferred if blank)
              <input value={site} onChange={(e) => setSite(e.target.value)} />
            </label>
          </>
        )}
        <label>
          Resume template
          <select
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
          >
            {TEMPLATES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cover letter tone
          <select value={tone} onChange={(e) => setTone(e.target.value)}>
            {TONES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          Dry run (produce artifacts, no submission)
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Working…" : dryRun ? "Preview" : "Apply"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="card">
          <h2>Result</h2>
          <p>
            Status: <strong>{result.app_status || "—"}</strong> (saga{" "}
            {result.saga_id || "—"})
          </p>
          {result.notes && result.notes.length > 0 && (
            <ul>
              {result.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          )}
          {result.artifacts && result.artifacts.resume_pdf && (
            <p className="muted">Resume: {result.artifacts.resume_pdf}</p>
          )}
          {result.app_status === "pending_approval" &&
            result.application_id && (
              <button onClick={approve} disabled={busy}>
                Approve &amp; submit
              </button>
            )}
        </div>
      )}
    </section>
  );
}
