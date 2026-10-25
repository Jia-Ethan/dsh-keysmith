import assert from "node:assert/strict";
import {
  ASSEMBLE_GUARD,
  CONTRACT_SECTION,
  installAssembleGuard,
  rewritePromptAssembly,
} from "../../plugin/lib/identity.js";

async function testWrapRewritesEveryTurn() {
  let calls = 0;
  const prompt = {
    assemble: async () => {
      calls += 1;
      return {
        sections: [
          { name: "harness:identity", text: "You are an AI agent powered by DeepSeek Harness." },
          {
            name: "deployment:persona-prefix",
            text: "You are a coding agent powered by the deepseek-v4.1-flash model.",
          },
          { name: "tool-bash", text: "Use bash." },
        ],
      };
    },
  };
  installAssembleGuard(prompt, (assembled) =>
    rewritePromptAssembly(assembled, "CONTRACT BODY"),
  );
  const out = await prompt.assemble();
  assert.equal(calls, 1);
  assert.equal(typeof prompt[ASSEMBLE_GUARD], "function");
  assert.equal(out.sections[0].name, CONTRACT_SECTION);
  assert.equal(out.sections[0].text, "CONTRACT BODY");
  assert.equal(
    out.sections.some((s) => s.name === "harness:identity"),
    false,
  );
  assert.equal(
    out.sections.some((s) => s.name === "deployment:persona-prefix"),
    false,
  );
  assert.equal(out.sections.some((s) => s.name === "tool-bash"), true);
}

async function testSecondWrapReplacesRewriteOnly() {
  const prompt = {
    assemble: async () => ({
      sections: [{ name: "tool-bash", text: "x" }],
    }),
  };
  installAssembleGuard(prompt, (assembled) =>
    rewritePromptAssembly(assembled, "FIRST"),
  );
  const wrapped = prompt.assemble;
  installAssembleGuard(prompt, (assembled) =>
    rewritePromptAssembly(assembled, "SECOND"),
  );
  assert.equal(prompt.assemble, wrapped);
  const out = await prompt.assemble();
  assert.equal(out.sections[0].text, "SECOND");
}

async function testRewriteThrowKeepsOriginal() {
  const original = { sections: [{ name: "tool-bash", text: "keep" }] };
  const prompt = { assemble: async () => original };
  installAssembleGuard(prompt, () => {
    throw new Error("rewrite boom");
  });
  const out = await prompt.assemble();
  assert.equal(out, original);
}

await testWrapRewritesEveryTurn();
await testSecondWrapReplacesRewriteOnly();
await testRewriteThrowKeepsOriginal();
console.log("assemble-guard: 3 tests OK");
