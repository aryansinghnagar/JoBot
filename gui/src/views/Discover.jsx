import { useState } from "react";
import { useAsync } from "../lib/useAsync.js";

const DEFAULT_PORTALS = [
  ["greenhouse", "Greenhouse (API Apply)"],
  ["lever", "Lever (API Apply)"],
  ["linkedin", "LinkedIn (Easy Apply)"],
  ["workday", "Workday (Browser Apply)"],
  ["indeed", "Indeed (Search Only)"],
  ["ashby", "Ashby (Search Only)"],
  ["smartrecruiters", "SmartRecruiters (Search Only)"],
  ["careers", "Company Careers (Search Only)"],
];

const AUTO_APPLY_SITES = [
  "greenhouse",
  "lever",
  "linkedin",
  "workday",
  "naukri",
];

export function Discover({ rpc, onApply }) {
  const [portal, setPortal] = useState("linkedin");
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [company, setCompany] = useState("");
  const [limit, setLimit] = useState(25);
  const [query, setQuery] = useState(null);
  const sites = useAsync(() => rpc.listSites(), [rpc]);

  const { loading, data, error } = useAsync(
    () => (query ? rpc.discoverJobs(query) : Promise.resolve(null)),
    [query, rpc],
  );

  const run = (e) => {
    e.preventDefault();
    setQuery({
      portal,
      keywords,
      location,
      limit: Number(limit),
      ...(company ? { company } : {}),
    });
  };

  const isKnown = (site) => DEFAULT_PORTALS.some(([key]) => key === site);

  return (
    <section>
      <h1>Discover Jobs</h1>
      <form className="form" onSubmit={run}>
        <label>
          Portal / Job Board
          <select value={portal} onChange={(e) => setPortal(e.target.value)}>
            {DEFAULT_PORTALS.map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
            {(sites?.sites || [])
              .filter((s) => !isKnown(s))
              .map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
          </select>
        </label>
        <label>
          Keywords / Role
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="e.g. Software Engineer, React"
          />
        </label>
        <label>
          Location
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Remote, New York, London"
          />
        </label>
        <label>
          Company / Tenant (Optional)
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. toptal (Workday)"
          />
        </label>
        <label>
          Result Limit
          <input
            type="number"
            min="1"
            max="100"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          />
        </label>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? "Searching Jobs…" : "Search Jobs"}
        </button>
      </form>

      {error && (
        <div className="card error-box" style={{ marginTop: "1rem" }}>
          {error}
        </div>
      )}

      {data && data.postings && (
        <div style={{ marginTop: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "0.5rem",
            }}
          >
            <h2>Search Results ({data.postings.length})</h2>
            <div style={{ fontSize: "0.8rem", color: "#a6adc8" }}>
              <span style={{ marginRight: "1rem" }}>
                ⚡ <strong>1-Click:</strong> Auto-submission supported
              </span>
              <span>
                🔗 <strong>Assisted:</strong> Tailored helper supported
              </span>
            </div>
          </div>

          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Company</th>
                <th>Location</th>
                <th>Capability</th>
                <th style={{ textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.postings.map((job, i) => {
                const isAuto = AUTO_APPLY_SITES.includes(
                  (job.site || "").toLowerCase(),
                );
                return (
                  <tr key={i}>
                    <td>
                      <strong>{job.title}</strong>
                    </td>
                    <td>{job.company}</td>
                    <td>{job.location || "Remote / Unspecified"}</td>
                    <td>
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
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        className={`btn ${isAuto ? "btn-primary" : "btn-secondary"}`}
                        style={{ fontSize: "0.8rem", padding: "0.3rem 0.6rem" }}
                        onClick={() => onApply(job)}
                      >
                        {isAuto ? "Apply" : "Tailor & Assist"}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {data.postings.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="muted"
                    style={{ textAlign: "center", padding: "2rem" }}
                  >
                    {data.note || "No postings found matching your query."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
