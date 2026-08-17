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
  const [showBrowser, setShowBrowser] = useState(false);
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
      show_browser: showBrowser,
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
        <label className="check">
          <input
            type="checkbox"
            checked={showBrowser}
            onChange={(e) => setShowBrowser(e.target.checked)}
          />
          Supervised Co-Pilot (Show visible browser window during application)
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Working…" : dryRun ? "Preview" : "Apply"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h2>Application Summary</h2>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <span>Status:</span>
            <span className={`badge ${
              result.app_status === "submitted" || result.app_status === "verified"
                ? "badge-success"
                : result.app_status === "pending_approval"
                ? "badge-warning"
                : "badge-secondary"
            }`}>
              {result.dry_run
                ? "Dry Run / Preview Complete"
                : result.app_status === "pending_approval"
                ? "Awaiting Human Approval"
                : result.app_status === "submitted" || result.app_status === "verified"
                ? "Submitted Successfully"
                : result.app_status || "Completed"}
            </span>
          </div>

          {result.notes && result.notes.length > 0 && (
            <ul style={{ marginBottom: "0.75rem" }}>
              {result.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          )}

          {result.artifacts && result.artifacts.resume_pdf && (
            <p className="muted">Generated Resume: <code>{result.artifacts.resume_pdf}</code></p>
          )}

          {result.app_status === "pending_approval" && result.application_id && (
            <div style={{ marginTop: "1rem" }}>
              <button className="btn btn-primary" onClick={approve} disabled={busy}>
                {busy ? "Submitting..." : "Approve & Submit Now"}
              </button>
            </div>
          )}

          <details style={{ marginTop: "1rem", fontSize: "0.8rem", color: "#888" }}>
            <summary style={{ cursor: "pointer" }}>Technical identifiers</summary>
            <p style={{ margin: "0.25rem 0" }}>Application ID: <code>{result.application_id || "N/A"}</code></p>
            <p style={{ margin: "0.25rem 0" }}>Saga ID: <code>{result.saga_id || "N/A"}</code></p>
          </details>
        </div>
      )}
    </section>
  );
}
