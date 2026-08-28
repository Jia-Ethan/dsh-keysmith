import { describe, expect, it } from "vitest";
import {
  SCHEMA,
  extractJson,
  parseStatusReport,
  parseWriteReport,
  buildDeployArgs,
  buildStatusArgs,
} from "./parser.js";

const statusStdout = JSON.stringify({
  schema: SCHEMA,
  operation: "status",
  mode: "preview",
  ok: true,
  ready: true,
  dsh_dir: "/tmp/.dsh",
  residue: [],
  manifest: null,
  adapter_patch: { state: "absent", path: null, managed: false, already_patched: null },
  actions: [],
  warnings: [],
  blockers: [],
  exit_status: 0,
  error: null,
}, null, 2);

describe("extractJson", () => {
  it("parses the first complete object and ignores trailing noise", () => {
    expect(extractJson(`note\n${statusStdout}\nextra`)).toMatchObject({ schema: SCHEMA, operation: "status" });
  });
});

describe("parseStatusReport", () => {
  it("maps adapter patch state and not-installed health", () => {
    const model = parseStatusReport({ stdout: statusStdout, stderr: "", exit_code: 0, timed_out: false });
    expect(model.health).toBe("not-installed");
    expect(model.adapterPatch.state).toBe("absent");
    expect(model.ready).toBe(true);
  });
});

describe("parseWriteReport", () => {
  it("gates on blockers", () => {
    const report = parseWriteReport({
      stdout: JSON.stringify({
        schema: SCHEMA,
        operation: "deploy",
        mode: "preview",
        ok: false,
        actions: [{ action: "create", path: "/tmp/AGENTS.md", detail: "agents_md" }],
        warnings: [],
        blockers: ["unfinished transaction residue: x"],
        exit_status: 1,
        error: null,
      }),
      stderr: "",
      exit_code: 1,
      timed_out: false,
    });
    expect(report.gate.ok).toBe(false);
    expect(report.actions[0].action).toBe("create");
  });
});

describe("arg builders", () => {
  it("builds flag-style deploy/status args", () => {
    expect(buildDeployArgs({ file: "/x.md", name: "n", dshDir: "/tmp/.dsh" })).toEqual([
      "--file", "/x.md", "--name", "n", "--dsh-dir", "/tmp/.dsh",
    ]);
    expect(buildStatusArgs({ dshDir: "/tmp/.dsh" })).toEqual(["--status", "--dsh-dir", "/tmp/.dsh"]);
  });
});
