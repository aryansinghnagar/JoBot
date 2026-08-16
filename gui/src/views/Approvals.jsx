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

  return (
    <section className="view">
      <h2>Pending Human Approvals</h2>
      <p className="muted">
        Durable human-in-the-loop gates requiring your explicit confirmation before submission.
      </p>

      {error && <div className="card error-box">{error}</div>}

      {loading ? (
        <p className="muted">Loading approvals...</p>
      ) : approvals.length === 0 ? (
        <div className="card">
          <p className="muted">No pending approvals. All submitted applications are approved or automated.</p>
        </div>
      ) : (
        <div className="approval-list">
          {approvals.map((appr) => (
            <div key={appr.id} className="card" style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>Approval ID: <code>{appr.id}</code></strong>
                <span className="badge badge-warning">{appr.status}</span>
              </div>
              <p style={{ margin: "0.5rem 0" }}>
                <strong>Application:</strong> <code>{appr.application_id || "N/A"}</code> | <strong>Action:</strong> {appr.action_type}
              </p>
              <pre style={{ background: "#111", padding: "0.5rem", borderRadius: "4px", fontSize: "0.85rem", overflowX: "auto" }}>
                {JSON.stringify(appr.action_payload, null, 2)}
              </pre>
              <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
                <button
                  className="btn btn-primary"
                  disabled={decidingId === appr.id}
                  onClick={() => handleDecision(appr.id, "APPROVED")}
                >
                  {decidingId === appr.id ? "Submitting..." : "Approve & Submit"}
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
