import { useState } from "react";
import { useAsync } from "../lib/useAsync.js";

export function Settings({ rpc }) {
  const doctor = useAsync(() => rpc.doctor(), [rpc]);
  const config = useAsync(() => rpc.configShow(), [rpc]);
  const digest = useAsync(() => rpc.digest(7), [rpc]);
  const traces = useAsync(() => rpc.traces(), [rpc]);

  return (
    <section>
      <h1>Settings &amp; Preferences</h1>
      <p className="muted">
        Manage your AI connections, verify system health, and review activity
        digests.
      </p>

      <AiConfigCard rpc={rpc} onUpdate={config.reload} />

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>System Diagnostics</h2>
        {doctor.loading ? (
          <p className="muted">Running diagnostics…</p>
        ) : doctor.error ? (
          <p className="error">{doctor.error}</p>
        ) : (
          <table style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>Component Check</th>
                <th>Status</th>
                <th>Diagnostic Detail</th>
              </tr>
            </thead>
            <tbody>
              {doctor.data.checks.map((c, i) => {
                const statusLabel = c.warn
                  ? c.ok
                    ? "PASS"
                    : "WARN"
                  : c.ok
                    ? "PASS"
                    : "FAIL";
                const badgeClass =
                  statusLabel === "PASS"
                    ? "badge-success"
                    : statusLabel === "WARN"
                      ? "badge-warning"
                      : "badge-danger";
                return (
                  <tr key={i}>
                    <td>
                      <strong>{c.label}</strong>
                    </td>
                    <td>
                      <span className={`badge ${badgeClass}`}>
                        {statusLabel}
                      </span>
                    </td>
                    <td className="muted">{c.detail}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>Active Configuration</h2>
        {config.loading ? (
          <p className="muted">Loading configuration…</p>
        ) : config.error ? (
          <p className="error">{config.error}</p>
        ) : (
          <table style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>Key</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(config.data.config || {}).map(([k, v]) => (
                <tr key={k}>
                  <td>
                    <code>{k}</code>
                  </td>
                  <td>
                    <strong>{String(v)}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>Weekly Activity Digest (Preview)</h2>
        {digest.loading ? (
          <p className="muted">Generating preview…</p>
        ) : digest.error ? (
          <p className="error">{digest.error}</p>
        ) : (
          <>
            <p>
              <strong>{digest.data.subject}</strong>
            </p>
            <pre
              className="digest"
              style={{
                background: "#111",
                padding: "1rem",
                borderRadius: "4px",
                overflowX: "auto",
              }}
            >
              {digest.data.text}
            </pre>
          </>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>Diagnostic Support Bundle</h2>
        <p className="muted">
          Export a sanitized, redacted archive of doctor diagnostics and site
          health logs for troubleshooting.
        </p>
        <ExportBundleButton rpc={rpc} />
      </div>

      <details className="card">
        <summary style={{ cursor: "pointer", fontWeight: "bold" }}>
          Advanced: Execution Traces &amp; Telemetry
        </summary>
        <div style={{ marginTop: "1rem" }}>
          {traces.loading ? (
            <p className="muted">Loading traces…</p>
          ) : traces.error ? (
            <p className="error">{traces.error}</p>
          ) : traces.data.runs.length === 0 ? (
            <p className="muted">No execution traces recorded.</p>
          ) : (
            <ul className="counts">
              {traces.data.runs.map((run) => (
                <li key={run.run_id}>
                  <span>
                    <code>{run.run_id}</code>
                  </span>
                  <strong>{run.span_count} spans recorded</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>
    </section>
  );
}

function ExportBundleButton({ rpc }) {
  const [exporting, setExporting] = useState(false);
  const [exportedPath, setExportedPath] = useState(null);
  const [error, setError] = useState(null);

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    try {
      const res = await rpc.exportDiagnostics();
      setExportedPath(res.path);
    } catch (err) {
      setError(err?.message || "Failed to export diagnostic bundle");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      <button
        className="btn btn-secondary"
        onClick={handleExport}
        disabled={exporting}
      >
        {exporting
          ? "Generating Bundle…"
          : "Export Redacted Diagnostic Bundle (.zip)"}
      </button>
      {exportedPath && (
        <p style={{ marginTop: "0.5rem", color: "#10b981" }}>
          ✓ Saved to: <code>{exportedPath}</code>
        </p>
      )}
      {error && (
        <p className="error" style={{ marginTop: "0.5rem" }}>
          {error}
        </p>
      )}
    </div>
  );
}

function AiConfigCard({ rpc, onUpdate }) {
  const [provider, setProvider] = useState("gemini");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [error, setError] = useState(null);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!apiKey && provider !== "ollama") {
      setError(`Please provide an API key for ${provider}.`);
      return;
    }
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      await rpc.configSet("llm.default_provider", provider);
      if (apiKey) {
        await rpc.configSet(`api_keys.${provider}`, apiKey);
      }
      setMsg(`✓ ${provider.toUpperCase()} provider connected & active.`);
      setApiKey("");
      if (onUpdate) onUpdate();
    } catch (err) {
      setError(
        err?.user_message || err?.message || "Failed to update AI settings",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h2>AI Intelligence &amp; Provider Settings</h2>
      <p className="muted">
        Configure the LLM engine used for tailoring resumes and generating
        grounded responses.
      </p>

      <form
        onSubmit={handleSave}
        className="form"
        style={{ marginTop: "1rem" }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "1rem",
          }}
        >
          <label>
            Active AI Provider
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                setMsg(null);
                setError(null);
              }}
            >
              <option value="gemini">
                Google Gemini (Recommended / Free Tier)
              </option>
              <option value="anthropic">
                Anthropic Claude (High Precision)
              </option>
              <option value="openai">OpenAI (GPT-4o)</option>
              <option value="ollama">Local Ollama (Offline / Private)</option>
            </select>
          </label>

          {provider !== "ollama" && (
            <label>
              Update API Key
              <input
                type="password"
                placeholder={`Paste new ${provider} API key`}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </label>
          )}
        </div>

        {provider === "gemini" && (
          <p
            className="muted"
            style={{ fontSize: "0.8rem", margin: "0.25rem 0 0.75rem 0" }}
          >
            Need a key?{" "}
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noreferrer"
              style={{ color: "#89b4fa", textDecoration: "underline" }}
            >
              Get a free Gemini API key from Google AI Studio
            </a>
          </p>
        )}

        <button
          type="submit"
          className="btn btn-primary"
          disabled={busy}
          style={{ fontSize: "0.85rem" }}
        >
          {busy ? "Saving…" : "Save & Activate Provider"}
        </button>

        {msg && (
          <p
            style={{
              color: "#10b981",
              marginTop: "0.5rem",
              fontSize: "0.85rem",
            }}
          >
            {msg}
          </p>
        )}
        {error && (
          <p
            className="error"
            style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}
          >
            {error}
          </p>
        )}
      </form>
    </div>
  );
}
