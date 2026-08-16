import { useState } from "react";
import { useAsync } from "../lib/useAsync.js";

const DEFAULT_PORTALS = [
  ["linkedin", "LinkedIn"],
  ["indeed", "Indeed"],
  ["lever", "Lever"],
  ["ashby", "Ashby"],
  ["smartrecruiters", "SmartRecruiters"],
  ["greenhouse", "Greenhouse"],
  ["careers", "Careers pages"],
  ["mock_ats", "Mock ATS (local test)"],
  ["workday", "Workday (company tenant)"],
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
          Portal
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
          Keywords
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
        </label>
        <label>
          Location
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </label>
        <label>
          Company / tenant
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. toptal (Workday)"
          />
        </label>
        <label>
          Limit
          <input
            type="number"
            min="1"
            max="100"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {data && data.postings && (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Company</th>
              <th>Location</th>
              <th>Site</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.postings.map((job, i) => (
              <tr key={i}>
                <td>{job.title}</td>
                <td>{job.company}</td>
                <td>{job.location}</td>
                <td>{job.site}</td>
                <td>
                  <button onClick={() => onApply(job)}>Apply</button>
                </td>
              </tr>
            ))}
            {data.postings.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  {data.note || "No postings returned."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
