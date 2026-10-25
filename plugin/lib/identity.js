/**
 * Assemble-time identity strip and contract pin.
 *
 * dsh-purge (Apache-2.0) showed the winning load path: rewrite the
 * assembled system prompt every turn, strip the host coding-agent line,
 * and pin the operator contract at the front. This module copies that
 * *load path*, not purge's persona or host-file patches.
 *
 * Order is HARNESS_IDENTITY - 1 (host default -1000 → -1001), the same
 * portable first-slot trick 山君 uses. Assemble wrapping still runs
 * after waterfall so a scoped `deployment:persona-prefix` cannot hide
 * the contract.
 */

export const CONTRACT_SECTION = "dsh-keysmith:contract";
export const ASSEMBLE_GUARD = Symbol.for("dsh-keysmith.assembleGuard");

const PERSONA_PREFIX_NAMES = new Set([
  "deployment:persona-prefix",
  "persona-prefix",
]);
const IDENTITY_SECTION_NAMES = new Set([
  "harness:identity",
  "deployment:persona-prefix",
  "persona-prefix",
  "deployment:persona",
  "persona",
]);

export function stripHarnessPersona(text) {
  if (typeof text !== "string" || text.length === 0) return text;
  return text
    .replace(/You are an AI agent powered by DeepSeek Harness\.?\s*/g, "")
    .replace(/You are a helpful software engineer assistant\.?\s*/gi, "")
    .replace(/你是一个有帮助的软件工程师助手[。.]?\s*/g, "")
    .replace(
      /You are a coding agent powered by the \{\{model\}\} model, running on the DeepSeek Harness\. Your working directory is \{\{cwd\}\}\.?\s*/g,
      "",
    )
    .replace(
      /You are a coding agent powered by the \{\{model\}\} model, running on the DeepSeek Harness\.?\s*/g,
      "",
    )
    .replace(
      /You are a coding agent powered by the \{\{model\}\} model\. Your working directory is \{\{cwd\}\}\.?\s*/g,
      "",
    )
    .replace(
      /You are a coding agent powered by the [^\n]+? model, running on the DeepSeek Harness\.?\s*/g,
      "",
    )
    .replace(/You are a coding agent powered by the [^\n]+? model\.?\s*/g, "")
    .replace(/You are Claude Code, Anthropic's official CLI for Claude\.?\s*/g, "")
    .replace(/You are Claude,?[^\n]*/g, "")
    .replace(/我是 Claude[^\n]*/g, "")
    .replace(/我是 DeepSeek(?:驱动)?的? AI(?:编程)?助手[，,]?[^\n]*/g, "")
    .replace(/你好！?我是 DeepSeek[^\n]*/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/ \n/g, "\n")
    .trim();
}

export function escapeDshInterpolation(text) {
  const src = String(text || "");
  if (!src.includes("{{")) return src;
  const allowed = new Set(["cwd", "model", "provider"]);
  return src.replace(/\{\{([^{}]*)\}\}|(\{\{)/g, (all, name, open) => {
    if (name !== undefined && allowed.has(name.trim())) return all;
    if (open) return "{ {";
    return `{ {${name}}}`;
  });
}

function sectionText(section) {
  if (!section) return "";
  return typeof section.text === "function" ? "" : String(section.text || "");
}

export function rewritePromptAssembly(assembled, contractText) {
  const contract = escapeDshInterpolation(String(contractText || "").trim());
  const sections = Array.isArray(assembled?.sections) ? assembled.sections.slice() : [];
  const rewritten = [];
  for (const section of sections) {
    if (!section || section.name === CONTRACT_SECTION) continue;
    const raw = sectionText(section);
    const stripped = stripHarnessPersona(raw);
    if (IDENTITY_SECTION_NAMES.has(section.name) && !stripped) continue;
    if (PERSONA_PREFIX_NAMES.has(section.name) && !stripped) continue;
    rewritten.push(stripped === raw ? section : { ...section, text: stripped });
  }
  rewritten.unshift({
    name: CONTRACT_SECTION,
    text: contract,
    interpolate: true,
  });
  const contexts = Array.isArray(assembled?.contexts)
    ? assembled.contexts.map((entry) => {
        const raw = sectionText(entry);
        const stripped = stripHarnessPersona(raw);
        return stripped === raw ? entry : { ...entry, text: stripped };
      })
    : assembled?.contexts;
  return { ...assembled, sections: rewritten, contexts };
}

export function contractOrder(systemPrompt) {
  const identityOrder =
    systemPrompt && typeof systemPrompt.getSectionOrder === "function"
      ? systemPrompt.getSectionOrder("HARNESS_IDENTITY")
      : undefined;
  return (Number.isFinite(identityOrder) ? identityOrder : -1000) - 1;
}

export function registerContractSection(ctx, contractText) {
  const prompt = ctx.systemPrompt;
  if (!prompt || typeof prompt.section !== "function") return;
  const text = escapeDshInterpolation(String(contractText || "").trim());
  const order = contractOrder(prompt);
  ctx.effect(() =>
    prompt.section({
      name: CONTRACT_SECTION,
      order,
      text,
      interpolate: true,
    }),
  );
}

export function installAssembleGuard(prompt, rewrite) {
  if (!prompt || typeof rewrite !== "function") return;
  if (prompt[ASSEMBLE_GUARD]) {
    prompt[ASSEMBLE_GUARD] = rewrite;
    return;
  }
  const original = prompt.assemble;
  if (typeof original !== "function") return;
  const wrapped = async function assembleWithKeysmith(...args) {
    let assembled;
    try {
      assembled = await original.apply(this, args);
    } catch (err) {
      try {
        console.warn("[dsh-keysmith] assemble threw:", err && err.message);
      } catch {
        /* ignore */
      }
      throw err;
    }
    try {
      const fn = prompt[ASSEMBLE_GUARD];
      return typeof fn === "function" ? fn(assembled, args[0]) : assembled;
    } catch (err) {
      try {
        console.warn("[dsh-keysmith] assemble rewrite threw:", err && err.message);
      } catch {
        /* ignore */
      }
      return assembled;
    }
  };
  prompt[ASSEMBLE_GUARD] = rewrite;
  try {
    Object.defineProperty(prompt, "assemble", {
      configurable: true,
      enumerable: false,
      writable: true,
      value: wrapped,
    });
  } catch {
    prompt.assemble = wrapped;
  }
}

export function bindAssembleWaterfall(ctx, rewrite) {
  if (!ctx || typeof ctx.on !== "function") return;
  ctx.on("system-prompt/assemble", async (assembly, context, next) => {
    let assembled = assembly;
    try {
      assembled = await next();
    } catch (err) {
      try {
        console.warn("[dsh-keysmith] assemble waterfall rejected:", err && err.message);
      } catch {
        /* ignore */
      }
      assembled = assembly;
    }
    try {
      return rewrite(assembled, context);
    } catch {
      return assembled;
    }
  });
}
