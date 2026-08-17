export function Help() {
  return (
    <section>
      <h1>Help &amp; Platform Guide</h1>
      <p className="muted">
        Learn how JoBot works, which platforms support automated submissions, and how candidate data is protected.
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>Supported Platforms &amp; Submission Capabilities</h2>
        <table style={{ width: "100%", marginTop: "0.5rem" }}>
          <thead>
            <tr>
              <th>Platform</th>
              <th>Supported Operations</th>
              <th>Submission Method</th>
              <th>Requirements</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Greenhouse</strong></td>
              <td>Discovery, Parsing, Direct Submission</td>
              <td><span className="badge badge-success">Direct HTTP API</span></td>
              <td>None (public board endpoints)</td>
            </tr>
            <tr>
              <td><strong>Lever</strong></td>
              <td>Discovery, Parsing, Direct Submission</td>
              <td><span className="badge badge-success">Direct HTTP API</span></td>
              <td>None (public postings API)</td>
            </tr>
            <tr>
              <td><strong>Workday</strong></td>
              <td>Discovery, Parsing, Form Submission</td>
              <td><span className="badge badge-warning">Browser Automation</span></td>
              <td><code>JOBOT_RUN_LIVE_BROWSER=1</code></td>
            </tr>
            <tr>
              <td><strong>LinkedIn Easy Apply</strong></td>
              <td>Job Search, Easy Apply Modal Solver</td>
              <td><span className="badge badge-warning">Browser Automation</span></td>
              <td><code>JOBOT_RUN_LIVE_BROWSER=1</code></td>
            </tr>
            <tr>
              <td><strong>Naukri</strong></td>
              <td>Job Search, Direct Form Fill</td>
              <td><span className="badge badge-warning">Browser Automation</span></td>
              <td><code>JOBOT_RUN_LIVE_BROWSER=1</code></td>
            </tr>
            <tr>
              <td><strong>Indeed / Glassdoor / Ashby / Workable</strong></td>
              <td>Job Discovery &amp; Search Scraping</td>
              <td><span className="badge badge-secondary">Discovery Only</span></td>
              <td>Submissions raise capability error</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>4-Step Workflow</h2>
        <ol style={{ paddingLeft: "1.25rem", lineHeight: "1.8" }}>
          <li>
            <strong>1. Seed Your Profile &amp; Facts:</strong> Use <code>jobot profile init</code> or upload your resume with <code>jobot import-resume</code> to populate verified candidate facts.
          </li>
          <li>
            <strong>2. Discover Matching Jobs:</strong> Use the <strong>Discover</strong> tab or CLI (<code>jobot scrape</code>) to search across supported job boards.
          </li>
          <li>
            <strong>3. Tailor Materials with Grounding:</strong> JoBot automatically generates tailored resumes and cover letters grounded in your profile facts with prompt injection defense.
          </li>
          <li>
            <strong>4. Human Review &amp; Submit:</strong> Verify drafted answers in the <strong>Approvals</strong> tab before authorizing final submission.
          </li>
        </ol>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2>Privacy, Security &amp; Safety Guarantees</h2>
        <ul style={{ paddingLeft: "1.25rem", lineHeight: "1.8" }}>
          <li>
            <strong>Encrypted Local Storage:</strong> All profile data, vault secrets, and application records stay on your computer under AES-256 Fernet encryption locked to your OS keyring.
          </li>
          <li>
            <strong>Prompt Injection Defense:</strong> External job postings are sanitized against override attacks and jailbreaks before LLM interpolation.
          </li>
          <li>
            <strong>Zero Simulated Submissions:</strong> JoBot never fabricates application receipts. Unsupported platforms cleanly refuse submission rather than faking success.
          </li>
          <li>
            <strong>Audit Evidence:</strong> Every submitted application records timestamped requests and cryptographic hashes in your local evidence folder (<code>~/.jobot/evidence/</code>).
          </li>
        </ul>
      </div>
    </section>
  );
}
