import { describe, expect, it, vi } from "vitest";
import {
  JobotRpc,
  RpcClient,
  RpcError,
  stdioTransport,
} from "../src/lib/rpc.js";

class FakeTransport {
  constructor() {
    this.sent = [];
    this.listener = () => {};
    this.closed = false;
  }

  write(line) {
    this.sent.push(line);
  }

  onMessage(fn) {
    this.listener = fn;
  }

  emit(line) {
    this.listener(line);
  }

  close() {
    this.closed = true;
  }
}

describe("RpcClient framing", () => {
  it("sends JSON-RPC 2.0 requests with incrementing ids", () => {
    const t = new FakeTransport();
    const client = new RpcClient(t);
    client.call("ping");
    client.call("status");

    const [a, b] = t.sent.map((line) => JSON.parse(line));
    expect(a.jsonrpc).toBe("2.0");
    expect(a.method).toBe("ping");
    expect(a.id).toBe(1);
    expect(b.id).toBe(2);
    expect(a.params).toEqual({});
  });

  it("resolves a matching response", async () => {
    const t = new FakeTransport();
    const client = new RpcClient(t);
    const promise = client.call("ping");
    t.emit(
      JSON.stringify({ jsonrpc: "2.0", result: { status: "pong" }, id: 1 }),
    );
    await expect(promise).resolves.toEqual({ status: "pong" });
  });

  it("rejects with an RpcError on a JSON-RPC error", async () => {
    const t = new FakeTransport();
    const client = new RpcClient(t);
    const promise = client.call("bogus");
    t.emit(
      JSON.stringify({
        jsonrpc: "2.0",
        error: { code: -32601, message: "Method 'bogus' not found" },
        id: 1,
      }),
    );
    await expect(promise).rejects.toMatchObject({ code: -32601 });
  });

  it("ignores notifications and malformed lines", async () => {
    const t = new FakeTransport();
    const client = new RpcClient(t);
    const promise = client.call("ping");
    t.emit("{not json");
    t.emit(JSON.stringify({ jsonrpc: "2.0", method: "note" }));
    t.emit(JSON.stringify({ jsonrpc: "2.0", result: "ok", id: 1 }));
    await expect(promise).resolves.toBe("ok");
  });

  it("rejects pending calls on close", async () => {
    const t = new FakeTransport();
    const client = new RpcClient(t);
    const promise = client.call("ping");
    client.close();
    await expect(promise).rejects.toMatchObject({ code: -32000 });
  });
});

describe("JobotRpc typed methods", () => {
  it("maps typed methods to the sidecar snake_case surface", () => {
    const t = new FakeTransport();
    const rpc = new JobotRpc(new RpcClient(t));
    rpc.approve("app_1");
    rpc.scheduleAdd("0 9 * * 1", "run");
    rpc.digest(14);
    rpc.discoverJobs({ portal: "linkedin", limit: 5, company: "toptal" });

    const calls = t.sent.map((line) => JSON.parse(line));
    expect(calls[0].method).toBe("approve");
    expect(calls[0].params).toEqual({ application_id: "app_1" });
    expect(calls[1].params).toEqual({ cron: "0 9 * * 1", command: "run" });
    expect(calls[2].params).toEqual({ period_days: 14 });
    expect(calls[3].params).toEqual({
      portal: "linkedin",
      limit: 5,
      company: "toptal",
    });
  });

  it("exposes the full RPC surface", () => {
    const t = new FakeTransport();
    const rpc = new JobotRpc(new RpcClient(t));
    const methods = [
      "ping",
      "status",
      "profileInfo",
      "listSites",
      "discoverJobs",
      "apply",
      "approve",
      "applications",
      "trackerStats",
      "campaignStatus",
      "pause",
      "resume",
      "scheduleList",
      "scheduleAdd",
      "scheduleRemove",
      "digest",
      "doctor",
      "configShow",
      "configGet",
      "configSet",
      "configUnset",
      "traces",
    ];
    for (const m of methods) {
      expect(typeof rpc[m]).toBe("function");
    }
  });
});

describe("stdioTransport", () => {
  it("spawns `jobot sidecar` and forwards framed output", async () => {
    const handlers = {};
    const child = {
      stdout: {
        setEncoding() {},
        on(event, cb) {
          handlers[event] = cb;
        },
      },
      stdin: { write: vi.fn() },
      on() {},
      kill() {},
    };
    const spawnFn = vi.fn(() => child);
    const transport = stdioTransport({ spawnFn });

    expect(spawnFn).toHaveBeenCalledWith("jobot", ["sidecar"]);

    const messages = [];
    transport.onMessage((line) => messages.push(line));
    handlers.data(
      JSON.stringify({ jsonrpc: "2.0", result: "ok", id: 1 }) + "\n",
    );
    expect(messages).toEqual([
      JSON.stringify({ jsonrpc: "2.0", result: "ok", id: 1 }),
    ]);

    transport.write("hello\n");
    expect(child.stdin.write).toHaveBeenCalledWith("hello\n");
  });
});

describe("RpcError", () => {
  it("carries a JSON-RPC error code", () => {
    const err = new RpcError(-32602, "bad params");
    expect(err.code).toBe(-32602);
    expect(err.name).toBe("RpcError");
    expect(err.message).toBe("bad params");
  });
});
