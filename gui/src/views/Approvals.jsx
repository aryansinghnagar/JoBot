import { useEffect, useState } from "react";

export function Approvals({ rpc }) {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [decidingId, setDecidingId] = useState(null);
  const [error, setError] = useState(null);

  const loadApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await rpc.call("approvals_list", { status: "PENDING" });
      setApprovals(res?.approvals || []);
    } catch (err) {
      setError(err?.message || "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const handleDecision = async (id, decision) => {
    const actionLabel =
      decision === "APPROVED" ? "approve and submit" : "deny and cancel";
    if (
      !window.confirm(
        `Are you sure you want to ${actionLabel} this application?`,
      )
    ) {
      return;
    }
    setDecidingId(id);
    try {
      await rpc.call("approvals_decide", {
        approval_id: id,
        decision: decision,
        decided_by: "gui-human",
      });
      await loadApprovals();
    } catch (err) {
      alert("Decision failed: " + (err?.message || err));
    } finally {
      setDecidingId(null);
    }
  };

  const renderPayloadSummary = (payload) => {
    if (!payload || typeof payload !== "object") return null;

    const form = payload.form_values || payload.form || payload;
    const coverLetter = payload.cover_letter_text || form.cover_letter_text;
    const resumePath = payload.resume_path || form.resume_path;

    return (
      <div className="approval-summary" style={{ marginTop: "0.75rem" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "0.5rem",
            marginBottom: "0.75rem",
          }}
        >
          {form.name && (
            <div>
              <strong>Candidate:</strong> {form.name}
            </div>
          )}
          {form.email && (
            <div>
              <strong>Email:</strong> {form.email}
            </div>
          )}
          {form.phone && (
            <div>
              <strong>Phone:</strong> {form.phone}
            </div>
          )}
          {form.location && (
            <div>
              <strong>Location:</strong> {form.location}
            </div>
          )}
          {resumePath && (
            <div
              style={{
                gridColumn: "1 / -1",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <strong>Resume:</strong> <code>{resumePath}</code>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                onClick={() => rpc.openPath(resumePath)}
              >
                📄 Open PDF
              </button>
            </div>
          )}
        </div>

        {coverLetter && (
          <div style={{ marginBottom: "0.75rem" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <strong>Tailored Cover Letter:</strong>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                onClick={() => {
                  navigator.clipboard?.writeText(coverLetter);
                  alert("Copied cover letter to clipboard!");
                }}
              >
                📋 Copy Text
              </button>
            </div>
            <div
              style={{
                background: "#1a1a24",
                padding: "0.75rem",
                borderRadius: "4px",
                marginTop: "0.25rem",
                whiteSpace: "pre-wrap",
                fontSize: "0.9rem",
                maxHeight: "150px",
                overflowY: "auto",
                border: "1px solid #333",
              }}
            >
              {coverLetter}
            </div>
          </div>
        )}

        <details
          style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#888" }}
        >
          <summary style={{ cursor: "pointer" }}>View raw payload</summary>
          <pre
            style={{
              background: "#111",
              padding: "0.5rem",
              borderRadius: "4px",
              marginTop: "0.25rem",
              overflowX: "auto",
            }}
          >
            {JSON.stringify(payload, null, 2)}
          </pre>
        </details>
      </div>
    );
  };

  return (
    <section className="view">
      <h2>Pending Human Approvals</h2>
      <p className="muted">
        Review tailored responses and attached resumes before granting 1-click
        submission permission.
      </p>

      <div
        style={{
          background: "#181825",
          border: "1px solid #313244",
          padding: "0.75rem 1rem",
          borderRadius: "8px",
          marginBottom: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <span style={{ fontSize: "1.25rem" }}>🛡️</span>
        <span style={{ fontSize: "0.85rem", color: "#cdd6f4" }}>
          <strong>Zero-Fabrication Guarantee:</strong> JoBot never submits
          applications behind your back or invents facts. Review the drafted
          answers below and click <strong>Approve &amp; Submit</strong> when
          ready.
        </span>
      </div>

      {error && <div className="card error-box">{error}</div>}

      {loading ? (
        <p className="muted">Loading approvals...</p>
      ) : approvals.length === 0 ? (
        <div className="card">
          <p className="muted">
            No pending approvals. All applications are approved or completed.
          </p>
        </div>
      ) : (
        <div className="approval-list">
          {approvals.map((appr) => (
            <div
              key={appr.id}
              className="card"
              style={{ marginBottom: "1rem" }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <strong>
                  {appr.action_payload?.job_title
                    ? `${appr.action_payload.job_title} at ${appr.action_payload.company || "Company"}`
                    : `Application Request`}
                </strong>
                <span className="badge badge-warning">{appr.status}</span>
              </div>

              {renderPayloadSummary(appr.action_payload)}

              <div
                style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}
              >
                <button
                  className="btn btn-primary"
                  disabled={decidingId === appr.id}
                  onClick={() => handleDecision(appr.id, "APPROVED")}
                >
                  {decidingId === appr.id
                    ? "Submitting..."
                    : "Approve & Submit"}
                </button>
                <button
                  className="btn btn-danger"
                  disabled={decidingId === appr.id}
                  onClick={() => handleDecision(appr.id, "DENIED")}
                >
                  Deny / Cancel
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
