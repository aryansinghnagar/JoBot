// Tauri transport: spawns `jobot sidecar` via the shell plugin and speaks
// line-delimited JSON-RPC over the child's stdin/stdout. Only imported from
// the browser entry (never from node/vitest), so @tauri-apps/plugin-shell is
// resolved only inside the Tauri webview.
import { Command, EventEmitter } from "@tauri-apps/plugin-shell";
import { RpcClient, JobotRpc } from "./rpc.js";

export function tauriTransport() {
  let command;
  try {
    command = Command.sidecar("binaries/jobot-sidecar");
  } catch {
    command = Command.create("jobot", ["sidecar"]);
  }
  const emitter = new EventEmitter();
  const encoder = new TextEncoder();

  let onMessage = () => {};
  let buffer = "";
  const stdout = command.stdout.onEvent((event) => {
    if (event.event === "Data") {
      buffer += event.data;
      let idx;
      while ((idx = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 1);
        if (line.trim()) onMessage(line.trim());
      }
    }
  });
  command.stderr.onEvent((event) => {
    if (event.event === "Data") {
      // stderr carries jobot warnings; surface them in the UI shell only
    }
  });

  command.spawn();

  return {
    write(line) {
      command.write(encoder.encode(line));
    },
    onMessage(fn) {
      onMessage = fn;
    },
    close() {
      stdout.unlisten();
      try {
        command.kill();
      } catch {
        /* ignore */
      }
    },
  };
}

export function createTauriJobotRpc() {
  return new JobotRpc(new RpcClient(tauriTransport()));
}
