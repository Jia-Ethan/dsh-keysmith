import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({ invoke: (...args) => invokeMock(...args) }));

function createStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
    clear: () => values.clear(),
  };
}

let api;
let store;
let settings;

beforeEach(async () => {
  vi.resetModules();
  invokeMock.mockReset();
  vi.stubGlobal("localStorage", createStorage());
  settings = await import("./settings.js");
  store = await import("./store.js");
  store.resetOperationCoordinatorForTests();
  api = await import("./api.js");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchStatus", () => {
  it("calls --status --json and optional --dsh-dir / --lang", async () => {
    settings.saveSettings({ defaultDshDir: "/tmp/.dsh", lang: "en" });
    invokeMock.mockResolvedValue({
      stdout: JSON.stringify({
        schema: "dsh-keysmith/v1",
        operation: "status",
        mode: "preview",
        ok: true,
        ready: true,
        residue: [],
        adapter_patch: { state: "absent" },
        actions: [],
        warnings: [],
        blockers: [],
        exit_status: 0,
      }),
      stderr: "",
      exit_code: 0,
      timed_out: false,
    });
    const model = await api.fetchStatus();
    expect(model.health).toBe("not-installed");
    expect(invokeMock).toHaveBeenCalledWith("cli_run", expect.objectContaining({
      args: ["--status", "--dsh-dir", "/tmp/.dsh", "--lang", "en", "--json"],
    }));
  });
});

describe("previewDeploy / executeDeploy", () => {
  it("preview omits --yes; execute adds --yes", async () => {
    invokeMock.mockResolvedValue({
      stdout: JSON.stringify({
        schema: "dsh-keysmith/v1",
        operation: "deploy",
        mode: "preview",
        ok: true,
        actions: [],
        warnings: [],
        blockers: [],
        exit_status: 0,
      }),
      stderr: "",
      exit_code: 0,
      timed_out: false,
    });
    await api.previewDeploy({ name: "n" });
    expect(invokeMock.mock.calls[0][1].args).toEqual(["--name", "n", "--lang", "zh-CN", "--json"]);
    invokeMock.mockClear();
    invokeMock.mockResolvedValue({
      stdout: JSON.stringify({
        schema: "dsh-keysmith/v1",
        operation: "deploy",
        mode: "execute",
        ok: true,
        actions: [],
        warnings: [],
        blockers: [],
        exit_status: 0,
      }),
      stderr: "",
      exit_code: 0,
      timed_out: false,
    });
    await api.executeDeploy({ name: "n" });
    expect(invokeMock.mock.calls[0][1].args).toEqual(["--name", "n", "--yes", "--lang", "zh-CN", "--json"]);
  });
});
