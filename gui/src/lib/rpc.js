// Line-delimited JSON-RPC 2.0 client over a duplex transport.
// Transport-independent and framework-free so it can be unit-tested in node
// without a browser, a Tauri runtime, or a real `jobot` process.

export class RpcError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "RpcError";
    this.code = code;
  }
}

export class RpcClient {
  constructor(transport) {
    this.transport = transport;
    this.nextId = 1;
    this.pending = new Map();
    this.closed = false;
    this.transport.onMessage((line) => this._handle(line));
  }

  _handle(line) {
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      return;
    }
    if (msg.id === undefined || msg.id === null) return;
    const entry = this.pending.get(msg.id);
    if (!entry) return;
    this.pending.delete(msg.id);
    if (msg.error) {
      entry.reject(new RpcError(msg.error.code, msg.error.message));
    } else {
      entry.resolve(msg.result);
    }
  }

  call(method, params = {}) {
    if (this.closed) {
      return Promise.reject(new RpcError(-32000, "client closed"));
    }
    const id = this.nextId++;
    const payload = { jsonrpc: "2.0", method, params, id };
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.transport.write(JSON.stringify(payload) + "\n");
    });
  }

  close() {
    this.closed = true;
    this.transport.close();
    for (const p of this.pending.values()) {
      p.reject(new RpcError(-32000, "client closed"));
    }
    this.pending.clear();
  }
}

// Typed convenience layer matching the sidecar RPC surface (snake_case params).
export class JobotRpc {
  constructor(client) {
    this.client = client;
  }

  ping() {
    return this.client.call("ping");
  }
  status() {
    return this.client.call("status");
  }
  profileInfo() {
    return this.client.call("profile_info");
  }
  listSites() {
    return this.client.call("list_sites");
  }
  discoverJobs(params) {
    return this.client.call("discover_jobs", params);
  }
  apply(params) {
    return this.client.call("apply", params);
  }
  approve(applicationId) {
    return this.client.call("approve", { application_id: applicationId });
  }
  applications(limit = 50) {
    return this.client.call("applications", { limit });
  }
  trackerStats() {
    return this.client.call("tracker_stats");
  }
  campaignStatus() {
    return this.client.call("campaign_status");
  }
  pause() {
    return this.client.call("pause");
  }
  resume() {
    return this.client.call("resume");
  }
  scheduleList() {
    return this.client.call("schedule_list");
  }
  scheduleAdd(cron, command) {
    return this.client.call("schedule_add", { cron, command });
  }
  scheduleRemove(scheduleId) {
    return this.client.call("schedule_remove", { schedule_id: scheduleId });
  }
  digest(periodDays = 7) {
    return this.client.call("digest", { period_days: periodDays });
  }
  doctor() {
    return this.client.call("doctor");
  }
  configShow() {
    return this.client.call("config_show");
  }
  configGet(key) {
    return this.client.call("config_get", { key });
  }
  configSet(key, value) {
    return this.client.call("config_set", { key, value });
  }
  configUnset(key) {
    return this.client.call("config_unset", { key });
  }
  traces() {
    return this.client.call("traces");
  }
}

// Node/stdio transport: spawns a process and exchanges newline-delimited
// JSON-RPC over its stdin/stdout. `spawnFn` is injectable for tests.
export function stdioTransport({ spawnFn }) {
  const child = spawnFn("jobot", ["sidecar"]);
  let onMessage = () => {};
  let closed = false;

  child.stdout.setEncoding("utf8");
  let buffer = "";
  child.stdout.on("data", (chunk) => {
    buffer += chunk;
    let idx;
    while ((idx = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 1);
      if (line.trim()) onMessage(line.trim());
    }
  });
  child.on("exit", () => {
    closed = true;
  });

  return {
    write(line) {
      if (!closed) child.stdin.write(line);
    },
    onMessage(fn) {
      onMessage = fn;
    },
    close() {
      closed = true;
      try {
        child.kill();
      } catch {
        /* ignore */
      }
    },
  };
}

// Default: create a JobotRpc over a spawned `jobot sidecar` process.
export async function createJobotRpc() {
  const { spawn } = await import("node:child_process");
  const transport = stdioTransport({ spawnFn: spawn });
  return new JobotRpc(new RpcClient(transport));
}
