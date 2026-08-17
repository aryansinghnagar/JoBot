import { useEffect, useState } from "react";

export function Profile({ rpc }) {
  const [profile, setProfile] = useState(null);
  const [facts, setFacts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // New Fact Form State
  const [factType, setFactType] = useState("skill");
  const [factValue, setFactValue] = useState("");
  const [busyFact, setBusyFact] = useState(false);

  // Resume Ingest State
  const [resumePath, setResumePath] = useState("");
  const [busyResume, setBusyResume] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pInfo, fInfo] = await Promise.all([
        rpc.profileInfo().catch(() => null),
        rpc.candidateFacts().catch(() => ({ facts: [] })),
      ]);
      setProfile(pInfo);
      setFacts(fInfo.facts || []);
    } catch (err) {
      setError(err?.message || "Failed to load candidate truth profile");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [rpc]);

  const handleAddFact = async (e) => {
    e.preventDefault();
    if (!factValue.trim()) return;
    setBusyFact(true);
    setError(null);
    try {
      await rpc.recordCandidateFact(factType, factValue.trim());
      setFactValue("");
      setSuccess(`Added verified ${factType} to Candidate Truth Ledger.`);
      const fInfo = await rpc.candidateFacts();
      setFacts(fInfo.facts || []);
    } catch (err) {
      setError(err?.message || "Failed to record candidate fact");
    } finally {
      setBusyFact(false);
    }
  };

  const handleResumeSync = async (e) => {
    e.preventDefault();
    if (!resumePath.trim()) return;
    setBusyResume(true);
    setError(null);
    try {
      const res = await rpc.importResume(resumePath.trim());
      setSuccess(`Successfully imported resume. ${res.facts_seeded} truth facts recorded.`);
      await loadData();
    } catch (err) {
      setError(err?.message || "Failed to import resume");
    } finally {
      setBusyResume(false);
    }
  };

  if (loading) {
    return <section className="view"><p className="muted">Loading Candidate Truth Profile…</p></section>;
  }

  const personal = profile?.personal_info || {};
  const compensation = profile?.compensation || {};
  const customAnswers = profile?.custom_qa_answers || {};

  return (
    <section className="view">
      <div className="view-header">
        <h1>Candidate Truth Ledger &amp; Profile</h1>
        <p className="muted">
          Your immutable, locally-encrypted ground truth facts. JoBot strictly validates
          all generated resumes, cover letters, and application answers against these facts.
        </p>
      </div>

      {error && <div className="card error-box" style={{ marginBottom: "1rem" }}>{error}</div>}
      {success && <div className="card success-box" style={{ marginBottom: "1rem" }}>{success}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
        {/* Candidate Profile Details Card */}
        <div className="card">
          <h2>Candidate Summary</h2>
          {profile ? (
            <table style={{ width: "100%", fontSize: "0.95rem" }}>
              <tbody>
                <tr>
                  <td><strong>Full Name:</strong></td>
                  <td>{personal.first_name} {personal.last_name}</td>
                </tr>
                <tr>
                  <td><strong>Email:</strong></td>
                  <td><code>{personal.email}</code></td>
                </tr>
                <tr>
                  <td><strong>Phone:</strong></td>
                  <td>{personal.phone || "—"}</td>
                </tr>
                <tr>
                  <td><strong>Location:</strong></td>
                  <td>{personal.location_city || "Remote"}{personal.location_country ? `, ${personal.location_country}` : ""}</td>
                </tr>
                <tr>
                  <td><strong>Target Roles:</strong></td>
                  <td>{customAnswers["Target Titles"] || "Software Engineer"}</td>
                </tr>
                <tr>
                  <td><strong>Minimum Salary:</strong></td>
                  <td>{compensation.minimum_annual_base_usd ? `$${compensation.minimum_annual_base_usd.toLocaleString()}/yr` : "Not specified"}</td>
                </tr>
                <tr>
                  <td><strong>Notice Period:</strong></td>
                  <td>{compensation.notice_period_days ? `${compensation.notice_period_days} days` : "30 days"}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="muted">No encrypted profile found. Run Setup Wizard.</p>
          )}
        </div>

        {/* Sync from Resume File */}
        <div className="card">
          <h2>Sync / Update from Resume</h2>
          <p className="muted">Re-parse your latest PDF or Word resume to refresh ground truth facts.</p>
          <form className="form" onSubmit={handleResumeSync}>
            <label>
              Resume File Path
              <input
                placeholder="C:/Users/You/Documents/Resume.pdf"
                value={resumePath}
                onChange={(e) => setResumePath(e.target.value)}
              />
            </label>
            <button className="btn btn-secondary" type="submit" disabled={busyResume || !resumePath.trim()}>
              {busyResume ? "Extracting Truth Facts…" : "Sync Truth Ledger from Resume"}
            </button>
          </form>
        </div>
      </div>

      {/* Add Fact Inline Form */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>Add Verified Candidate Fact</h2>
        <p className="muted">Explicitly certify a skill, degree, project, or custom form answer into your ledger.</p>
        <form className="form" onSubmit={handleAddFact} style={{ display: "grid", gridTemplateColumns: "180px 1fr auto", gap: "0.75rem", alignItems: "end" }}>
          <label>
            Fact Category
            <select value={factType} onChange={(e) => setFactType(e.target.value)}>
              <option value="skill">Skill</option>
              <option value="education">Education / Degree</option>
              <option value="experience">Experience / Role</option>
              <option value="project">Project / Accomplishment</option>
              <option value="certification">Certification</option>
              <option value="custom_answer">Custom QA Answer</option>
            </select>
          </label>
          <label>
            Fact Statement / Value
            <input
              required
              placeholder="e.g. 5+ years experience building distributed backend systems in Python and Go"
              value={factValue}
              onChange={(e) => setFactValue(e.target.value)}
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busyFact}>
            {busyFact ? "Recording…" : "+ Record Fact"}
          </button>
        </form>
      </div>

      {/* Verified Truth Ledger Table */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2>Verified Ground Truth Ledger ({facts.length} Facts)</h2>
          <button className="btn btn-secondary" onClick={loadData}>↻ Refresh</button>
        </div>

        {facts.length === 0 ? (
          <p className="muted">No candidate facts recorded yet in the truth store.</p>
        ) : (
          <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #333", color: "#aaa" }}>
                <th style={{ padding: "0.6rem" }}>Type</th>
                <th style={{ padding: "0.6rem" }}>Verified Value</th>
                <th style={{ padding: "0.6rem" }}>Source</th>
                <th style={{ padding: "0.6rem" }}>Confidence</th>
                <th style={{ padding: "0.6rem" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {facts.map((f, idx) => (
                <tr key={f.id || idx} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: "0.6rem" }}>
                    <span className="badge" style={{ textTransform: "capitalize" }}>
                      {f.fact_type}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem", fontWeight: "500" }}>{f.fact_value}</td>
                  <td style={{ padding: "0.6rem", color: "#888", fontSize: "0.85rem" }}>{f.source}</td>
                  <td style={{ padding: "0.6rem", color: "#10b981", fontSize: "0.85rem" }}>
                    {(f.confidence * 100).toFixed(0)}%
                  </td>
                  <td style={{ padding: "0.6rem" }}>
                    <span style={{ color: "#10b981", fontSize: "0.85rem" }}>✓ Grounded</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
