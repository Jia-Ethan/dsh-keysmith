import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const mod = await import(
  pathToFileURL(
    path.resolve("plugin/scripts/ensure-profile-bundle.mjs"),
  ).href
);

function tmpProfile() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dsh-keysmith-profile-"));
  fs.writeFileSync(
    path.join(dir, "package.json"),
    JSON.stringify(
      {
        name: "dsh-profile-web",
        private: true,
        dsh: { profile: { bundles: ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"] } },
      },
      null,
      2,
    ) + "\n",
  );
  fs.writeFileSync(path.join(dir, "cordis.patch.yml"), "# empty\n[]\n");
  return dir;
}

function testEnsureDropsEmptyArray() {
  const out = mod.ensureKeysmithInsert("# comment\n[]\n");
  assert.equal(out.includes("[]"), false);
  const lines = out.split("\n").filter((ln) => ln.trim() && !ln.trim().startsWith("#"));
  assert.equal(lines[0].startsWith("- insert:"), true);
  assert.equal(mod.profileHasKeysmithBodyInsert(out), true);
}

function testDetectInsert() {
  const yes = "- insert:\n    - id: dsh-keysmith\n      name: dsh-keysmith\n";
  const no = "- insert:\n    - id: other\n      name: other\n";
  assert.equal(mod.profileHasKeysmithBodyInsert(yes), true);
  assert.equal(mod.profileHasKeysmithBodyInsert(no), false);
  assert.equal(mod.profileHasKeysmithBodyInsert(""), false);
}

function testInstallUninstall() {
  const dir = tmpProfile();
  process.env.INIT_CWD = dir;
  // Run install via the same helpers the postinstall uses.
  const pkgPath = path.join(dir, "package.json");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  pkg.dsh.profile.bundles.push("dsh-keysmith");
  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + "\n");
  const patchPath = path.join(dir, "cordis.patch.yml");
  fs.appendFileSync(patchPath, "\n- insert:\n    - id: dsh-keysmith\n      name: dsh-keysmith\n");
  assert.equal(mod.profileHasKeysmithBodyInsert(fs.readFileSync(patchPath, "utf8")), true);
  mod.uninstallFromProfile(dir);
  const afterPkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  assert.equal(afterPkg.dsh.profile.bundles.includes("dsh-keysmith"), false);
  assert.equal(mod.profileHasKeysmithBodyInsert(fs.readFileSync(patchPath, "utf8")), false);
  fs.rmSync(dir, { recursive: true, force: true });
}

testEnsureDropsEmptyArray();
testDetectInsert();
testInstallUninstall();
console.log("ensure-bundle: 3 tests OK");
