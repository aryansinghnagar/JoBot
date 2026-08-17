import { useState } from "react";

const TEMPLATES = ["default", "modern", "classic"];
const TONES = ["classic", "concise", "technical", "warm", "assertive"];

const AUTO_APPLY_SITES = [
  "greenhouse",
  "lever",
  "linkedin",
  "workday",
  "naukri",
];

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
  const [errorObj, setErrorObj] = useState(null);

  const isAuto = job
    ? AUTO_APPLY_SITES.includes((job.site || "").toLowerCase())
    : site
      ? AUTO_APPLY_SITES.includes(site.toLowerCase())
      : true;

  const run = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrorObj(null);
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
      setErrorObj({
        user_message:
          "Please select a job from Discover or enter a job posting URL.",
        action_hint:
          "Go to the Discover tab to search for jobs, or paste a link from LinkedIn/Workday.",
      });
      setBusy(false);
      return;
    }
    try {
      const res = await rpc.apply(params);
      setResult(res);
    } catch (err) {
      setErrorObj({
        user_message: err?.user_message || err?.message || String(err),
        action_hint: err?.action_hint || "",
        category: err?.category || "general",
      });
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!result || !result.application_id) return;
    setBusy(true);
    setErrorObj(null);
    try {
      const res = await rpc.approve(result.application_id);
      setResult(res);
    } catch (err) {
      setErrorObj({
        user_message: err?.user_message || err?.message || String(err),
        action_hint: err?.action_hint || "",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h1>Apply Cockpit</h1>
      {job ? (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <strong style={{ fontSize: "1.05rem" }}>{job.title}</strong>
              <div
                className="muted"
                style={{ fontSize: "0.85rem", marginTop: "0.2rem" }}
              >
                {job.company} — {job.location || "Remote"} ({job.site})
              </div>
            </div>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "0.2rem 0.5rem",
                borderRadius: "4px",
                background: isAuto ? "#1e3a2f" : "#2d2a1e",
                color: isAuto ? "#a6e3a1" : "#f9e2af",
                border: `1px solid ${isAuto ? "#3d6d53" : "#635832"}`,
              }}
            >
              {isAuto ? "⚡ 1-Click Auto-Apply" : "🔗 Assisted Apply"}
            </span>
          </div>

          {!isAuto && (
            <div
              style={{
                marginTop: "0.75rem",
                background: "#181825",
                padding: "0.6rem 0.8rem",
                borderRadius: "6px",
                fontSize: "0.8rem",
                color: "#f9e2af",
              }}
            >
              ℹ️ <strong>Assisted Apply Mode:</strong> JoBot will tailor your
              resume and cover letter. We will copy your tailored text to your
              clipboard and open the application link with 1 click.
            </div>
          )}
        </div>
      ) : (
        <p className="muted" style={{ marginBottom: "1rem" }}>
          Pick a job from Discover, or enter a saved job id / posting URL below.
        </p>
      )}

      <form className="form" onSubmit={run}>
        {!job && (
          <>
            <label>
              Saved Job ID (Optional)
              <input
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                placeholder="e.g. job_123"
              />
            </label>
            <label>
              Job Posting URL
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://boards.greenhouse.io/acme/jobs/101"
              />
            </label>
            <label>
              Job Board Site (Auto-detected if blank)
              <input
                value={site}
                onChange={(e) => setSite(e.target.value)}
                placeholder="e.g. greenhouse, linkedin, workday"
              />
            </label>
          </>
        )}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "1rem",
          }}
        >
          <label>
            Resume Template Style
            <select
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
            >
              {TEMPLATES.map((t) => (
                <option key={t} value={t}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Cover Letter Tone
            <select value={tone} onChange={(e) => setTone(e.target.value)}>
              {TONES.map((t) => (
                <option key={t} value={t}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="check">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          <strong>Review First (Dry Run):</strong> Tailor resume and draft
          materials without submitting immediately.
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={showBrowser}
            onChange={(e) => setShowBrowser(e.target.checked)}
          />
          <strong>Supervised Co-Pilot:</strong> Keep browser visible on your
          screen during submission.
        </label>

        <div style={{ marginTop: "0.5rem" }}>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy
              ? "Working on Application…"
              : dryRun
                ? "Tailor & Preview Draft"
                : "Apply to Job"}
          </button>
        </div>
      </form>

      {errorObj && (
        <div className="card error-box" style={{ marginTop: "1rem" }}>
          <strong>{errorObj.user_message}</strong>
          {errorObj.action_hint && (
            <p
              style={{
                marginTop: "0.4rem",
                fontSize: "0.85rem",
                color: "#f9e2af",
              }}
            >
              💡 {errorObj.action_hint}
            </p>
          )}
        </div>
      )}

      {result && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h2>Application Summary</h2>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "0.75rem",
            }}
          >
            <span>Status:</span>
            <span
              className={`badge ${
                result.app_status === "submitted" ||
                result.app_status === "verified"
                  ? "badge-success"
                  : result.app_status === "pending_approval"
                    ? "badge-warning"
                    : "badge-secondary"
              }`}
            >
              {result.dry_run
                ? "Dry Run / Preview Complete"
                : result.app_status === "pending_approval"
                  ? "Awaiting Human Approval"
                  : result.app_status === "submitted" ||
                      result.app_status === "verified"
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
            <div style={{ margin: "0.75rem 0" }}>
              <p className="muted" style={{ marginBottom: "0.4rem" }}>
                Generated Resume: <code>{result.artifacts.resume_pdf}</code>
              </p>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: "0.85rem" }}
                  onClick={() => rpc.openPath(result.artifacts.resume_pdf)}
                >
                  📄 Open Resume PDF
                </button>
                {result.artifacts.cover_letter_txt && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.85rem" }}
                    onClick={() =>
                      rpc.openPath(result.artifacts.cover_letter_txt)
                    }
                  >
                    ✉️ Open Cover Letter
                  </button>
                )}
              </div>
            </div>
          )}

          {result.app_status === "pending_approval" &&
            result.application_id && (
              <div style={{ marginTop: "1rem" }}>
                <button
                  className="btn btn-primary"
                  onClick={approve}
                  disabled={busy}
                >
                  {busy ? "Submitting..." : "Approve & Submit Now"}
                </button>
              </div>
            )}

          <details
            style={{ marginTop: "1rem", fontSize: "0.8rem", color: "#888" }}
          >
            <summary style={{ cursor: "pointer" }}>
              Technical identifiers
            </summary>
            <p style={{ margin: "0.25rem 0" }}>
              Application ID: <code>{result.application_id || "N/A"}</code>
            </p>
            <p style={{ margin: "0.25rem 0" }}>
              Saga ID: <code>{result.saga_id || "N/A"}</code>
            </p>
          </details>
        </div>
      )}
    </section>
  );
}
