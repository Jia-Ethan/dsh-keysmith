import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  CONTRACT_SECTION,
  rewritePromptAssembly,
  stripHarnessPersona,
  escapeDshInterpolation,
} from "../../plugin/lib/identity.js";

const root = path.dirname(fileURLToPath(new URL("../../plugin/lib/identity.js", import.meta.url)));
const contract = readFileSync(path.join(root, "contract.md"), "utf8");

function testStrip() {
  const src =
    "You are a coding agent powered by the deepseek-v4.1-flash model. Keep going.";
  const out = stripHarnessPersona(src);
  assert.equal(out, "Keep going.");
  assert.equal(stripHarnessPersona("You are an AI agent powered by DeepSeek Harness. Hi."), "Hi.");
}

function testEscape() {
  assert.equal(escapeDshInterpolation("powered by the {{model}} model"), "powered by the {{model}} model");
  assert.equal(escapeDshInterpolation("see {{cwd}}"), "see {{cwd}}");
  assert.equal(escapeDshInterpolation("keep {{unknown}}"), "keep { {unknown}}");
}

function testPinAndStrip() {
  const assembled = {
    sections: [
      { name: "harness:identity", text: "You are an AI agent powered by DeepSeek Harness." },
      {
        name: "deployment:persona-prefix",
        text: "You are a coding agent powered by the {{model}} model.",
      },
      { name: "tool-bash", text: "Use bash to run commands." },
    ],
    contexts: [
      { name: "approval", text: "You are a coding agent powered by the {{model}} model. Ask first." },
    ],
    tools: [],
    variables: { model: "deepseek-v4.1-flash" },
  };
  const out = rewritePromptAssembly(assembled, contract);
  assert.equal(out.sections[0].name, CONTRACT_SECTION);
  assert.ok(out.sections[0].text.includes("The request is X; the deliverable is X"));
  assert.ok(out.sections[0].text.includes("{{model}}"));
  assert.equal(
    out.sections.some((s) => s.name === "harness:identity"),
    false,
  );
  assert.equal(
    out.sections.some((s) => s.name === "deployment:persona-prefix"),
    false,
  );
  assert.equal(out.sections.some((s) => s.name === "tool-bash"), true);
  assert.equal(out.contexts[0].text, "Ask first.");
  assert.equal(out.variables.model, "deepseek-v4.1-flash");
}

function testIdempotentPin() {
  const once = rewritePromptAssembly(
    { sections: [{ name: CONTRACT_SECTION, text: "old" }, { name: "tool-bash", text: "x" }] },
    "NEW CONTRACT",
  );
  assert.equal(once.sections.filter((s) => s.name === CONTRACT_SECTION).length, 1);
  assert.equal(once.sections[0].text, "NEW CONTRACT");
}

testStrip();
testEscape();
testPinAndStrip();
testIdempotentPin();
console.log("identity: 4 tests OK");
