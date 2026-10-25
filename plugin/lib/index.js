import { readFileSync } from "node:fs";
import {
  bindAssembleWaterfall,
  installAssembleGuard,
  registerContractSection,
  rewritePromptAssembly,
} from "./identity.js";
import { applyLookup } from "./lookup.js";

export const name = "dsh-keysmith";
export const inject = ["systemPrompt", "tools"];

const CONTRACT_PATH = new URL("./contract.md", import.meta.url);

function loadContract() {
  try {
    return readFileSync(CONTRACT_PATH, "utf8");
  } catch {
    return "";
  }
}

function pluginVersion() {
  try {
    const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
    return String(pkg.version || "0.4.0");
  } catch {
    return "0.4.0";
  }
}

const objectOutput = {
  schema: { type: "object", additionalProperties: true },
  render: (_args, value) => [{ type: "text", text: JSON.stringify(value) }],
};

const profileTool = {
  name: "dsh_keysmith_profile",
  description: "Return dsh-keysmith plugin version and injection status.",
  parameters: { type: "object", properties: {}, additionalProperties: false },
  output: objectOutput,
  execute() {
    return {
      plugin: "dsh-keysmith",
      pluginVersion: pluginVersion(),
      pluginDisplayName: "DSH Keysmith",
      contractSection: "dsh-keysmith:contract",
      lookup: "in-plugin",
      hostPatches: false,
      autoRestart: false,
    };
  },
};

function bindProjection(ctx) {
  const anySchema = { parse: (value) => value };
  const def = {
    key: "dsh-keysmith",
    stateVersion: 1,
    stateSchema: anySchema,
    init: () => ({ active: true, plugin: "dsh-keysmith", version: pluginVersion() }),
    apply: (state) => state,
    wire: {
      viewSchema: anySchema,
      view: (state) => state,
    },
  };
  const register = (p) => {
    try {
      ctx.effect(() => p.register(def, "dsh-keysmith: dock projection"));
    } catch {
      /* host without sessionProjections */
    }
  };
  const projections = typeof ctx.get === "function" ? ctx.get("sessionProjections") : undefined;
  if (projections !== undefined) {
    register(projections);
    return;
  }
  if (typeof ctx.inject === "function") {
    ctx.inject(["sessionProjections"], (inner) => {
      const p = inner.get("sessionProjections");
      if (p !== undefined) register(p);
    });
  }
}

export function apply(ctx, _config = {}) {
  const contractText = loadContract();
  registerContractSection(ctx, contractText);

  const rewrite = (assembled) => rewritePromptAssembly(assembled, contractText);
  bindAssembleWaterfall(ctx, rewrite);
  if (ctx.systemPrompt) installAssembleGuard(ctx.systemPrompt, rewrite);

  try {
    applyLookup(ctx);
  } catch (err) {
    try {
      console.warn("[dsh-keysmith] lookup apply failed:", err && err.message);
    } catch {
      /* ignore */
    }
  }

  if (ctx.tools && typeof ctx.tools.register === "function") {
    ctx.effect(() => ctx.tools.register(profileTool));
  }

  bindProjection(ctx);
}

export default { name, inject, apply };
