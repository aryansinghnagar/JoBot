import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "../src/App.jsx";
import { Dashboard } from "../src/views/Dashboard.jsx";
import { Discover } from "../src/views/Discover.jsx";
import { Apply } from "../src/views/Apply.jsx";
import { Controls } from "../src/views/Controls.jsx";
import { Settings } from "../src/views/Settings.jsx";

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
      "Controls",
      "Settings",
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
    expect(html).toContain("Application Dashboard");
  });

  it("Discover", () => {
    const html = renderToString(
      <Discover rpc={stubRpc()} onApply={() => {}} />,
    );
    expect(html).toContain("Discover Jobs");
    expect(html).toContain("Mock ATS (local test)");
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
    expect(html).toContain("Dry run");
  });

  it("Controls", () => {
    const html = renderToString(<Controls rpc={stubRpc()} />);
    expect(html).toContain("Campaign Controls");
    expect(html).toContain("Pause");
  });

  it("Settings", () => {
    const html = renderToString(<Settings rpc={stubRpc()} />);
    expect(html).toContain("Settings &amp; Diagnostics");
    expect(html).toContain("Doctor");
  });
});
