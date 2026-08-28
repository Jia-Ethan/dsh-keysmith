// lib/api.js — 前端到 Rust 命令的薄封装。所有 CLI 调用一律带 --json。

import { invoke } from "@tauri-apps/api/core";
import { getSettings, normalizeCliPath } from "./settings.js";
import {
  parseStatusReport,
  parseWriteReport,
  buildDeployArgs,
  buildStatusArgs,
  buildUninstallArgs,
  buildRecoverArgs,
  buildLangArgs,
} from "./parser.js";
import { beginOperation, beginExclusiveOperation, endOperation } from "./store.js";

function invokeWithLease(acquireLease, command, payload, exhaustedMessage) {
  const operationLease = acquireLease();
  if (!operationLease) {
    return Promise.reject(new Error(exhaustedMessage));
  }
  try {
    return Promise.resolve(invoke(command, payload)).finally(() => {
      endOperation(operationLease);
    });
  } catch (error) {
    endOperation(operationLease);
    throw error;
  }
}

function invokeTrackedOperation(command, payload) {
  return invokeWithLease(
    beginOperation,
    command,
    payload,
    "Application exit is pending; refusing to start another backend operation.",
  );
}

function invokeExclusiveOperation(command, payload) {
  return invokeWithLease(
    beginExclusiveOperation,
    command,
    payload,
    "Another operation is in progress or application exit is pending; refusing to start a write operation.",
  );
}

export function cliRun(args, timeoutMs = 30_000) {
  const { cliPath } = getSettings();
  return invokeTrackedOperation("cli_run", {
    cliPath: cliPath || null,
    args,
    timeoutMs,
  });
}

export function cliRunExclusive(args, timeoutMs = 30_000) {
  const { cliPath } = getSettings();
  return invokeExclusiveOperation("cli_run", {
    cliPath: cliPath || null,
    args,
    timeoutMs,
  });
}

export function detectCli() {
  return invokeTrackedOperation("detect_cli");
}

export function cliVersion(cliPath) {
  return invokeTrackedOperation("cli_version", { cliPath: cliPath || null });
}

export function cliRuntime(cliPath) {
  return invokeTrackedOperation("cli_runtime", { cliPath: cliPath || null });
}

export async function resolveCli(
  cliPath,
  {
    detect = detectCli,
    getRuntime = cliRuntime,
    getVersion = cliVersion,
  } = {},
) {
  const manualPath = normalizeCliPath(cliPath);
  if (manualPath) {
    const version = await getVersion(manualPath);
    const runtime = await getRuntime(manualPath);
    return { path: manualPath, version, runtime };
  }

  const detected = await detect();
  const path = detected?.path || null;
  return {
    path,
    version: path ? await getVersion(path) : "",
    runtime: detected?.runtime || "",
  };
}

function withLangAndJson(args) {
  const { lang } = getSettings();
  return [...args, ...buildLangArgs(lang), "--json"];
}

export function readManifest(dshDir) {
  return invokeTrackedOperation("read_manifest", { codexDir: dshDir });
}

export async function fetchStatus({ dshDir } = {}) {
  const { defaultDshDir } = getSettings();
  const args = withLangAndJson(buildStatusArgs({ dshDir: dshDir || defaultDshDir }));
  const output = await cliRun(args);
  return parseStatusReport(output);
}

export function previewDeploy(options) {
  const { defaultDshDir } = getSettings();
  return cliRun(withLangAndJson(buildDeployArgs({ ...options, dshDir: options?.dshDir || defaultDshDir }))).then(parseWriteReport);
}

export function executeDeploy(options) {
  const { defaultDshDir } = getSettings();
  return cliRunExclusive(
    withLangAndJson([...buildDeployArgs({ ...options, dshDir: options?.dshDir || defaultDshDir }), "--yes"]),
    120_000,
  ).then(parseWriteReport);
}

export function previewUninstall(options) {
  const { defaultDshDir } = getSettings();
  return cliRun(withLangAndJson(buildUninstallArgs({ dshDir: options?.dshDir || defaultDshDir }))).then(parseWriteReport);
}

export function executeUninstall(options) {
  const { defaultDshDir } = getSettings();
  return cliRunExclusive(
    withLangAndJson([...buildUninstallArgs({ dshDir: options?.dshDir || defaultDshDir }), "--yes"]),
    120_000,
  ).then(parseWriteReport);
}

export function previewRecover(options) {
  const { defaultDshDir } = getSettings();
  return cliRun(withLangAndJson(buildRecoverArgs({ dshDir: options?.dshDir || defaultDshDir }))).then(parseWriteReport);
}

export function executeRecover(options) {
  const { defaultDshDir } = getSettings();
  return cliRunExclusive(
    withLangAndJson([...buildRecoverArgs({ dshDir: options?.dshDir || defaultDshDir }), "--yes"]),
    120_000,
  ).then(parseWriteReport);
}

export function isTauriMissing(err) {
  return (
    !window.__TAURI_INTERNALS__ ||
    (err && typeof err.message === "string" && err.message.includes("__TAURI"))
  );
}

export class CliError extends Error {
  constructor(output = {}) {
    const stdout = String(output.stdout ?? "");
    const stderr = String(output.stderr ?? "");
    const details = [stderr.trim(), stdout.trim()].filter(Boolean);
    super(details.join("\n\n") || `exit ${output.exit_code ?? "unknown"}`);
    this.name = "CliError";
    this.output = output;
    this.stdout = stdout;
    this.stderr = stderr;
    this.exitCode = output.exit_code ?? null;
    this.timedOut = Boolean(output.timed_out);
  }
}
