// lib/parser.js — dsh-keysmith JSON 契约（dsh-keysmith/v1）→ 视图模型

export const SCHEMA = "dsh-keysmith/v1";

export class ContractError extends Error {
  constructor(message, output = {}) {
    super(message);
    this.name = "ContractError";
    this.output = output;
    this.exitCode = output.exit_code ?? null;
    this.timedOut = Boolean(output.timed_out);
  }
}

export function extractJson(stdout) {
  const text = String(stdout ?? "");
  const start = text.indexOf("{");
  if (start === -1) return null;
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = start; i < text.length; i += 1) {
    const ch = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        try {
          return JSON.parse(text.slice(start, i + 1));
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asBool(value) {
  return value === true;
}

export function parseContract(output) {
  if (output?.timed_out) {
    throw new ContractError("CLI 执行超时", output);
  }
  const doc = extractJson(output?.stdout);
  if (!doc || typeof doc !== "object") {
    throw new ContractError("CLI 未输出稳定 JSON", output);
  }
  if (doc.schema !== undefined && doc.schema !== SCHEMA) {
    throw new ContractError(`不支持的契约版本: ${String(doc.schema)}`, output);
  }
  doc.exitCode = output?.exit_code ?? null;
  doc.stderr = String(output?.stderr ?? "");
  return doc;
}

export function mapAction(action) {
  return {
    action: typeof action?.action === "string" ? action.action : "unknown",
    path: typeof action?.path === "string" ? action.path : "",
    detail: typeof action?.detail === "string" ? action.detail : "",
  };
}

export function gateReport(report) {
  const reasons = [];
  if (report.exitCode !== 0) reasons.push(`exit ${report.exitCode ?? "unknown"}`);
  if (report.blockers.length > 0) reasons.push(...report.blockers);
  if (!report.ok && report.blockers.length === 0) {
    reasons.push(report.error || "ok=false");
  }
  return { ok: reasons.length === 0, reasons };
}

export function parseWriteReport(output) {
  const doc = parseContract(output);
  const blockers = asArray(doc.blockers).map(String);
  const report = {
    schema: doc.schema ?? null,
    operation: typeof doc.operation === "string" ? doc.operation : "unknown",
    mode: doc.mode === "execute" ? "execute" : "preview",
    ok: asBool(doc.ok),
    actions: asArray(doc.actions).map(mapAction),
    warnings: asArray(doc.warnings).map(String),
    blockers,
    error: typeof doc.error === "string" ? doc.error : null,
    dshDir: typeof doc.dsh_dir === "string" ? doc.dsh_dir : null,
    name: typeof doc.name === "string" ? doc.name : null,
    residue: asArray(doc.residue),
    manifest: doc.manifest && typeof doc.manifest === "object" ? doc.manifest : null,
    adapterPatch: mapAdapter(doc.adapter_patch),
    deploymentId: typeof doc.deployment_id === "string" ? doc.deployment_id : null,
    backups: asArray(doc.backups),
    reloadRequired: false,
    exitCode: doc.exitCode,
    stderr: doc.stderr,
    raw: doc,
  };
  report.gate = gateReport(report);
  return report;
}

export function mapAdapter(adapter) {
  const a = adapter && typeof adapter === "object" ? adapter : {};
  return {
    state: typeof a.state === "string" ? a.state : "unknown",
    path: typeof a.path === "string" ? a.path : null,
    managed: asBool(a.managed),
    alreadyPatched: a.already_patched === true,
  };
}

export function parseStatusReport(output) {
  const doc = parseContract(output);
  const residue = asArray(doc.residue);
  const model = {
    schema: doc.schema ?? null,
    operation: typeof doc.operation === "string" ? doc.operation : "status",
    ok: asBool(doc.ok),
    ready: asBool(doc.ready),
    dshDir: typeof doc.dsh_dir === "string" ? doc.dsh_dir : null,
    residue,
    manifest: doc.manifest && typeof doc.manifest === "object" ? doc.manifest : null,
    adapterPatch: mapAdapter(doc.adapter_patch),
    blockers: asArray(doc.blockers).map(String),
    warnings: asArray(doc.warnings).map(String),
    error: typeof doc.error === "string" ? doc.error : null,
    exitCode: doc.exitCode,
    stderr: doc.stderr,
    raw: doc,
  };
  if (residue.length > 0) model.health = "recovery-required";
  else if (model.manifest) model.health = "healthy";
  else model.health = "not-installed";
  return model;
}

export function buildLangArgs(lang) {
  return lang ? ["--lang", lang] : [];
}

export function buildDirArgs(dshDir) {
  return dshDir ? ["--dsh-dir", dshDir] : [];
}

export function buildDeployArgs({ file, name, dshDir } = {}) {
  const args = [];
  if (file) args.push("--file", file);
  if (name) args.push("--name", name);
  args.push(...buildDirArgs(dshDir));
  return args;
}

export function buildStatusArgs({ dshDir } = {}) {
  return ["--status", ...buildDirArgs(dshDir)];
}

export function buildUninstallArgs({ dshDir } = {}) {
  return ["--uninstall", ...buildDirArgs(dshDir)];
}

export function buildRecoverArgs({ dshDir } = {}) {
  return ["--recover", ...buildDirArgs(dshDir)];
}
