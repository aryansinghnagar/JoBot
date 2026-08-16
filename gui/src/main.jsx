import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.jsx";
import "./styles.css";

async function boot() {
  const isTauri =
    typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
  let rpc = null;
  try {
    if (isTauri) {
      const { createTauriJobotRpc } = await import("./lib/tauriTransport.js");
      rpc = createTauriJobotRpc();
    } else {
      const { createJobotRpc } = await import("./lib/rpc.js");
      rpc = await createJobotRpc();
    }
  } catch (err) {
    console.error("jobot sidecar unavailable:", err);
  }
  const root = document.getElementById("root");
  createRoot(root).render(
    <StrictMode>
      <App rpc={rpc} />
    </StrictMode>,
  );
}

boot();
