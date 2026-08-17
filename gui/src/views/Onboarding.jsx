import { useState } from "react";

export function Onboarding({ rpc, onComplete }) {
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Form State
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [skills, setSkills] = useState("Python, SQL, React");
  const [targetRoles, setTargetRoles] = useState(
    "Software Engineer, Backend Developer",
  );
  const [yearsExp, setYearsExp] = useState("3");
  const [minSalary, setMinSalary] = useState("100000");

  // AI Config State
  const [llmProvider, setLlmProvider] = useState("gemini");
  const [apiKey, setApiKey] = useState("");
  const [aiTested, setAiTested] = useState(false);

  // Resume Import State
  const [resumePath, setResumePath] = useState("");

  const handleImportResume = async (e) => {
    e.preventDefault();
    if (!resumePath) return;
    setBusy(true);
    setError(null);
    try {
      const res = await rpc.importResume(resumePath);
      if (res.name) {
        const parts = res.name.split(" ");
        setFirstName(parts[0] || "");
        setLastName(parts.slice(1).join(" ") || "");
      }
      if (res.email) setEmail(res.email);
      if (res.skills && res.skills.length > 0) setSkills(res.skills.join(", "));
      setSuccessMsg(
        `Resume parsed successfully (${res.facts_seeded} facts extracted).`,
      );
    } catch (err) {
      setError(err?.message || "Failed to import resume");
    } finally {
      setBusy(false);
    }
  };

  const handleTestAi = async () => {
    if (!apiKey && llmProvider !== "ollama") {
      setError("Please enter an API key for " + llmProvider);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await rpc.configSet("llm.default_provider", llmProvider);
      if (apiKey) {
        await rpc.configSet(`api_keys.${llmProvider}`, apiKey);
      }
      setAiTested(true);
      setSuccessMsg(
        `${llmProvider.toUpperCase()} provider connected & configured.`,
      );
    } catch (err) {
      setError(err?.message || "AI configuration failed");
    } finally {
      setBusy(false);
    }
  };

  const handleFinish = async () => {
    if (!firstName || !email) {
      setError("First name and email are required to create your profile.");
      setStep(1);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await rpc.profileSave({
        first_name: firstName,
        last_name: lastName,
        email: email,
        phone: phone,
        location_city: city,
        location_country: country,
        skills: skills,
        target_roles: targetRoles,
        years_experience: yearsExp,
        min_salary: Number(minSalary) || 0,
      });
      if (onComplete) onComplete();
    } catch (err) {
      setError(err?.message || "Failed to save profile");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="view"
      style={{ maxWidth: "700px", margin: "0 auto", padding: "1rem" }}
    >
      <div style={{ textAlign: "center", marginBottom: "2rem" }}>
        <h1>Welcome to JoBot</h1>
        <p className="muted">
          Set up your encrypted candidate truth profile and AI preferences to
          get started.
        </p>
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: "0.5rem",
            marginTop: "1rem",
          }}
        >
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background:
                  step === s ? "#4f46e5" : step > s ? "#10b981" : "#222",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: "bold",
                fontSize: "0.9rem",
              }}
            >
              {step > s ? "✓" : s}
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="card error-box" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      {successMsg && (
        <div className="card success-box" style={{ marginBottom: "1rem" }}>
          {successMsg}
        </div>
      )}

      {step === 1 && (
        <div className="card">
          <h2>Step 1: Candidate Personal Details</h2>
          <p className="muted">
            Your personal facts will be encrypted locally in your OS keyring
            vault.
          </p>

          <div
            style={{
              background: "#1a1a24",
              padding: "1rem",
              borderRadius: "6px",
              marginBottom: "1.5rem",
              border: "1px solid #333",
            }}
          >
            <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem" }}>
              Have an existing resume file?
            </h3>
            <div
              style={{
                border: "2px dashed #4f46e5",
                borderRadius: "8px",
                padding: "1.5rem",
                textAlign: "center",
                background: "#1e1e2e",
                cursor: "pointer",
                marginBottom: "1rem",
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={async (e) => {
                e.preventDefault();
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  const f = e.dataTransfer.files[0];
                  const path = f.path || f.name;
                  setResumePath(path);
                  setBusy(true);
                  setError(null);
                  try {
                    const res = await rpc.importResume(path);
                    if (res.name) {
                      const parts = res.name.split(" ");
                      setFirstName(parts[0] || "");
                      setLastName(parts.slice(1).join(" ") || "");
                    }
                    if (res.email) setEmail(res.email);
                    if (res.skills && res.skills.length > 0)
                      setSkills(res.skills.join(", "));
                    setSuccessMsg(
                      `Extracted ${res.facts_seeded} facts from ${f.name}!`,
                    );
                  } catch (err) {
                    setError(
                      err?.user_message ||
                        err?.message ||
                        "Failed to parse resume",
                    );
                  } finally {
                    setBusy(false);
                  }
                }
              }}
            >
              <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📄</div>
              <strong>Drag &amp; Drop your Resume PDF here</strong>
              <p
                className="muted"
                style={{ fontSize: "0.85rem", margin: "0.5rem 0" }}
              >
                Supports PDF, DOCX, or TXT
              </p>
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  gap: "0.5rem",
                  marginTop: "0.5rem",
                }}
              >
                <input
                  type="text"
                  placeholder="Or enter file path (e.g. C:/Documents/Resume.pdf)"
                  value={resumePath}
                  onChange={(e) => setResumePath(e.target.value)}
                  style={{ maxWidth: "350px", fontSize: "0.85rem" }}
                />
                <button
                  className="btn btn-secondary"
                  onClick={handleImportResume}
                  disabled={busy || !resumePath}
                  style={{ fontSize: "0.85rem" }}
                >
                  {busy ? "Parsing…" : "Autofill"}
                </button>
              </div>
            </div>

            {skills && (
              <div
                style={{
                  background: "#181825",
                  padding: "0.75rem",
                  borderRadius: "6px",
                  marginBottom: "1rem",
                }}
              >
                <span style={{ fontSize: "0.8rem", color: "#a6adc8" }}>
                  Extracted Skills Preview:
                </span>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "0.4rem",
                    marginTop: "0.4rem",
                  }}
                >
                  {skills.split(",").map((s, idx) => (
                    <span
                      key={idx}
                      style={{
                        background: "#313244",
                        color: "#cdd6f4",
                        padding: "0.2rem 0.5rem",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                      }}
                    >
                      {s.trim()}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              setStep(2);
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1rem",
              }}
            >
              <label>
                First Name *
                <input
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="e.g. Jane"
                />
              </label>
              <label>
                Last Name
                <input
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="e.g. Doe"
                />
              </label>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1rem",
              }}
            >
              <label>
                Email Address *
                <input
                  required
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="jane@example.com"
                />
              </label>
              <label>
                Phone Number
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+1 415 555 0199"
                />
              </label>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1rem",
              }}
            >
              <label>
                City
                <input
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="San Francisco"
                />
              </label>
              <label>
                Country
                <input
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  placeholder="USA"
                />
              </label>
            </div>

            <div style={{ marginTop: "1rem", textAlign: "right" }}>
              <button className="btn btn-primary" type="submit">
                Continue to Role Preferences →
              </button>
            </div>
          </form>
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <h2>Step 2: Skills &amp; Job Search Preferences</h2>
          <p className="muted">
            These facts anchor the AI grounding engine and matching ladder.
          </p>

          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              setStep(3);
            }}
          >
            <label>
              Technical &amp; Domain Skills (comma-separated)
              <input
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
                placeholder="Python, FastAPI, SQL, Docker, TypeScript"
              />
            </label>

            <label>
              Target Job Titles
              <input
                value={targetRoles}
                onChange={(e) => setTargetRoles(e.target.value)}
                placeholder="Senior Backend Engineer, Full Stack Developer"
              />
            </label>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1rem",
              }}
            >
              <label>
                Years of Relevant Experience
                <input
                  type="number"
                  min="0"
                  max="50"
                  value={yearsExp}
                  onChange={(e) => setYearsExp(e.target.value)}
                />
              </label>
              <label>
                Minimum Desired Annual Salary (USD)
                <input
                  type="number"
                  min="0"
                  step="5000"
                  value={minSalary}
                  onChange={(e) => setMinSalary(e.target.value)}
                />
              </label>
            </div>

            <div
              style={{
                marginTop: "1.5rem",
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => setStep(1)}
              >
                ← Back
              </button>
              <button className="btn btn-primary" type="submit">
                Continue to AI Setup →
              </button>
            </div>
          </form>
        </div>
      )}

      {step === 3 && (
        <div className="card">
          <h2>Step 3: Connect AI Provider</h2>
          <p className="muted">
            JoBot uses AI to tailor resumes and draft customized cover letters.
            Choose your preferred AI provider below.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "0.75rem",
              marginBottom: "1.25rem",
            }}
          >
            {[
              {
                id: "gemini",
                name: "Google Gemini",
                desc: "Recommended (Free tier available, ultra-fast)",
                badge: "Free Tier",
              },
              {
                id: "anthropic",
                name: "Anthropic Claude",
                desc: "High precision & natural writing style",
                badge: "Pro",
              },
              {
                id: "openai",
                name: "OpenAI GPT-4o",
                desc: "Industry standard capabilities",
                badge: "Popular",
              },
              {
                id: "ollama",
                name: "Local Ollama",
                desc: "100% private, runs offline on your PC",
                badge: "Offline",
              },
            ].map((p) => (
              <div
                key={p.id}
                onClick={() => {
                  setLlmProvider(p.id);
                  setAiTested(false);
                }}
                style={{
                  border:
                    llmProvider === p.id
                      ? "2px solid #4f46e5"
                      : "1px solid #313244",
                  background: llmProvider === p.id ? "#1e1e2e" : "#181825",
                  padding: "0.75rem",
                  borderRadius: "8px",
                  cursor: "pointer",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <strong>{p.name}</strong>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      background: "#313244",
                      padding: "0.15rem 0.4rem",
                      borderRadius: "4px",
                    }}
                  >
                    {p.badge}
                  </span>
                </div>
                <p
                  className="muted"
                  style={{ fontSize: "0.75rem", margin: "0.3rem 0 0 0" }}
                >
                  {p.desc}
                </p>
              </div>
            ))}
          </div>

          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              setStep(4);
            }}
          >
            {llmProvider === "gemini" && (
              <div
                style={{
                  background: "#181825",
                  padding: "0.75rem",
                  borderRadius: "6px",
                  marginBottom: "1rem",
                  border: "1px solid #313244",
                }}
              >
                <span style={{ fontSize: "0.85rem" }}>
                  💡 <strong>Need a free Gemini key?</strong>
                </span>
                <p
                  className="muted"
                  style={{ fontSize: "0.8rem", margin: "0.3rem 0 0.5rem 0" }}
                >
                  Google provides free API access for personal use with no
                  credit card required.
                </p>
                <a
                  href="https://aistudio.google.com/app/apikey"
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    color: "#89b4fa",
                    fontSize: "0.8rem",
                    textDecoration: "underline",
                  }}
                >
                  👉 Click here to get your free Gemini Key from Google AI
                  Studio (opens in browser)
                </a>
              </div>
            )}

            {llmProvider !== "ollama" && (
              <label>
                {llmProvider.toUpperCase()} API Key
                <input
                  type="password"
                  placeholder={`Paste your ${llmProvider} API key here`}
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    setAiTested(false);
                  }}
                />
              </label>
            )}

            <div style={{ marginTop: "0.5rem", marginBottom: "1rem" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleTestAi}
                disabled={busy}
              >
                {busy ? "Testing…" : "Save & Verify Connection"}
              </button>
              {aiTested && (
                <span style={{ marginLeft: "0.5rem", color: "#10b981" }}>
                  ✓ Verified
                </span>
              )}
            </div>

            <div
              style={{
                marginTop: "1.5rem",
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => setStep(2)}
              >
                ← Back
              </button>
              <button className="btn btn-primary" type="submit">
                Review &amp; Launch →
              </button>
            </div>
          </form>
        </div>
      )}

      {step === 4 && (
        <div className="card">
          <h2>Step 4: Confirmation &amp; Launch</h2>
          <p className="muted">
            Review your configuration before opening the JoBot cockpit.
          </p>

          <table style={{ width: "100%", marginBottom: "1.5rem" }}>
            <tbody>
              <tr>
                <td>
                  <strong>Candidate Name:</strong>
                </td>
                <td>
                  {firstName} {lastName}
                </td>
              </tr>
              <tr>
                <td>
                  <strong>Email:</strong>
                </td>
                <td>{email}</td>
              </tr>
              <tr>
                <td>
                  <strong>Location:</strong>
                </td>
                <td>
                  {city || "Remote"}
                  {country ? `, ${country}` : ""}
                </td>
              </tr>
              <tr>
                <td>
                  <strong>Skills:</strong>
                </td>
                <td>
                  <code>{skills}</code>
                </td>
              </tr>
              <tr>
                <td>
                  <strong>Target Roles:</strong>
                </td>
                <td>{targetRoles}</td>
              </tr>
              <tr>
                <td>
                  <strong>AI Provider:</strong>
                </td>
                <td>
                  <code>{llmProvider}</code>
                </td>
              </tr>
            </tbody>
          </table>

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => setStep(3)}
            >
              ← Back
            </button>
            <button
              className="btn btn-primary"
              onClick={handleFinish}
              disabled={busy}
            >
              {busy ? "Saving Profile…" : "Complete Setup & Launch Dashboard"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
