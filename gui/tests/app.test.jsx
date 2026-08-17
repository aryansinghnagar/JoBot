import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "../src/App.jsx";
import { Dashboard } from "../src/views/Dashboard.jsx";
import { Discover } from "../src/views/Discover.jsx";
import { Apply } from "../src/views/Apply.jsx";
import { Controls } from "../src/views/Controls.jsx";
import { Settings } from "../src/views/Settings.jsx";

import { Approvals } from "../src/views/Approvals.jsx";
import { Health } from "../src/views/Health.jsx";

function stubRpc() {
  return new Proxy(
    {},
    {
      get() {
        return async () => ({});
      },
    },
  );
}

describe("GUI shell", () => {
  it("renders the app frame with navigation", () => {
    const html = renderToString(<App rpc={stubRpc()} />);
    expect(html).toContain("JoBot Desktop");
    for (const label of [
      "Dashboard",
      "Discover",
      "Apply",
      "Approvals",
      "Health",
      "Controls",
      "Settings",
      "Help &amp; Guide",
    ]) {
      expect(html).toContain(label);
    }
  });

  it("shows the sidecar-unavailable message when rpc is null", () => {
    const html = renderToString(<App rpc={null} />);
    expect(html).toContain("Sidecar unavailable");
  });
});

describe("views render without a live sidecar", () => {
  it("Dashboard", () => {
    const html = renderToString(<Dashboard rpc={stubRpc()} />);
    expect(html).toContain("Application Cockpit");
    expect(html).toContain("Kanban Board");
  });

  it("Discover", () => {
    const html = renderToString(
      <Discover rpc={stubRpc()} onApply={() => {}} />,
    );
    expect(html).toContain("Discover Jobs");
    expect(html).toContain("Greenhouse (API Apply)");
  });

  it("Apply (with a selected job)", () => {
    const job = {
      job_id: "j1",
      title: "Engineer",
      company: "Acme",
      site: "workday",
    };
    const html = renderToString(<Apply rpc={stubRpc()} job={job} />);
    expect(html).toContain("Engineer");
    expect(html).toContain("Review First (Dry Run)");
    expect(html).toContain("1-Click Auto-Apply");
  });

  it("Approvals", () => {
    const html = renderToString(<Approvals rpc={stubRpc()} />);
    expect(html).toContain("Pending Human Approvals");
  });

  it("Health", () => {
    const html = renderToString(<Health rpc={stubRpc()} />);
    expect(html).toContain("Portal &amp; ATS Site Health");
  });

  it("Controls", () => {
    const html = renderToString(<Controls rpc={stubRpc()} />);
    expect(html).toContain("Campaign Controls");
    expect(html).toContain("Pause");
  });

  it("Settings", () => {
    const html = renderToString(<Settings rpc={stubRpc()} />);
    expect(html).toContain("Settings &amp; Preferences");
    expect(html).toContain("System Diagnostics");
    expect(html).toContain("AI Intelligence &amp; Provider Settings");
  });

  it("Onboarding", async () => {
    const { Onboarding } = await import("../src/views/Onboarding.jsx");
    const html = renderToString(
      <Onboarding rpc={stubRpc()} onComplete={() => {}} />,
    );
    expect(html).toContain("Welcome to JoBot");
    expect(html).toContain("Candidate Personal Details");
  });

  it("Profile & Truth Ledger", async () => {
    const { Profile } = await import("../src/views/Profile.jsx");
    const html = renderToString(<Profile rpc={stubRpc()} />);
    expect(html).toContain("Candidate Truth Ledger");
  });
});
