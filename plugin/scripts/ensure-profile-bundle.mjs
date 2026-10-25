#!/usr/bin/env node
/**
 * When installed into a DSH profile, write two bits:
 *   1. dsh.profile.bundles += "dsh-keysmith"
 *   2. an insert in the profile cordis.patch.yml
 *
 * pnpm add / dsh plugin add do not write the insert themselves.
 * Skip entirely when this install is the plugin repo, not a profile.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const NAME = "dsh-keysmith";

const INSERT_BLOCK = ["- insert:", "    - id: dsh-keysmith", "      name: dsh-keysmith", ""].join(
  "\n",
);

function readJson(fp) {
  try {
    return JSON.parse(fs.readFileSync(fp, "utf8"));
  } catch {
    return null;
  }
}

function isProfilePkg(pkg) {
  if (!pkg || typeof pkg !== "object") return false;
  if (typeof pkg.name === "string" && pkg.name.startsWith("dsh-profile-")) return true;
  return Array.isArray(pkg.dsh?.profile?.bundles);
}

function findProfileDir() {
  const seeds = [process.env.INIT_CWD, process.env.npm_config_local_prefix, process.cwd()].filter(
    Boolean,
  );
  for (const seed of seeds) {
    let dir = path.resolve(seed);
    for (let i = 0; i < 8; i += 1) {
      if (isProfilePkg(readJson(path.join(dir, "package.json")))) return dir;
      const parent = path.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  }
  return "";
}

export function dropEmptySequenceDocument(text) {
  const lines = String(text || "").split(/\r?\n/).filter((line) => line.trim() !== "[]");
  let body = lines.join("\n");
  if (String(text || "").endsWith("\n") && body && !body.endsWith("\n")) body += "\n";
  return body;
}

export function ensureKeysmithInsert(text) {
  let body = dropEmptySequenceDocument(text);
  if (profileHasKeysmithBodyInsert(body)) {
    return body.endsWith("\n") ? body : `${body}\n`;
  }
  if (body && !body.endsWith("\n")) body += "\n";
  if (body.trim() && !body.endsWith("\n\n")) body += "\n";
  return `${body}${INSERT_BLOCK}`;
}

export function profileHasKeysmithBodyInsert(text) {
  const lines = String(text || "").split(/\r?\n/);
  let insertIndent = -1;
  for (const line of lines) {
    if (/^-\s*insert:\s*$/.test(line) || /^\s+-\s*insert:\s*$/.test(line)) {
      insertIndent = (line.match(/^[ \t]*/) || [""])[0].length;
      continue;
    }
    if (insertIndent < 0) continue;
    const indent = (line.match(/^[ \t]*/) || [""])[0].length;
    const trimmed = line.trim();
    if (trimmed && indent <= insertIndent && /^-\s/.test(trimmed)) {
      insertIndent = -1;
      if (/^-\s*insert:\s*$/.test(trimmed)) {
        insertIndent = indent;
      }
      continue;
    }
    if (/^-\s*id:\s*dsh-keysmith\s*$/.test(trimmed)) return true;
  }
  return false;
}

function ensureProfileInsert(profileDir) {
  const fp = path.join(profileDir, "cordis.patch.yml");
  let text = "";
  try {
    text = fs.readFileSync(fp, "utf8");
  } catch {
    text = "";
  }
  const next = ensureKeysmithInsert(text);
  if (next === text) {
    process.stdout.write(`dsh-keysmith: insert already in ${fp}\n`);
    return false;
  }
  fs.writeFileSync(fp, next, "utf8");
  process.stdout.write(`dsh-keysmith: wrote body insert (${fp})\n`);
  return true;
}

function stripKeysmithInsert(text) {
  const lines = String(text || "").split(/\r?\n/);
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^-\s*insert:\s*$/.test(line) || /^\s+-\s*insert:\s*$/.test(line)) {
      const block = [line];
      let j = i + 1;
      const baseIndent = (line.match(/^[ \t]*/) || [""])[0].length;
      while (j < lines.length) {
        const nxt = lines[j];
        const indent = (nxt.match(/^[ \t]*/) || [""])[0].length;
        const trimmed = nxt.trim();
        if (trimmed && indent <= baseIndent && /^-\s/.test(trimmed) && !/insert:/.test(trimmed)) {
          break;
        }
        if (trimmed === "" && j + 1 < lines.length) {
          const peek = lines[j + 1];
          const peekIndent = (peek.match(/^[ \t]*/) || [""])[0].length;
          if (peekIndent <= baseIndent && /^-\s/.test(peek.trim()) && !/insert:/.test(peek.trim())) {
            break;
          }
        }
        block.push(nxt);
        j += 1;
      }
      const joined = block.join("\n");
      if (/id:\s*dsh-keysmith/.test(joined) && !/id:\s*(?!dsh-keysmith)\S+/.test(joined.replace(/id:\s*dsh-keysmith/, ""))) {
        i = j;
        continue;
      }
      if (/id:\s*dsh-keysmith/.test(joined) && block.filter((l) => /^\s+-\s*id:\s*/.test(l)).length === 1) {
        i = j;
        continue;
      }
    }
    out.push(line);
    i += 1;
  }
  return out.join("\n").replace(/\n{3,}/g, "\n\n");
}

export function uninstallFromProfile(profileDir) {
  const fp = path.join(profileDir, "package.json");
  const pkg = readJson(fp);
  if (pkg?.dsh?.profile && Array.isArray(pkg.dsh.profile.bundles)) {
    pkg.dsh.profile.bundles = pkg.dsh.profile.bundles.filter((item) => item !== NAME);
    fs.writeFileSync(fp, `${JSON.stringify(pkg, null, 2)}\n`, "utf8");
  }
  const patchFp = path.join(profileDir, "cordis.patch.yml");
  try {
    const text = fs.readFileSync(patchFp, "utf8");
    fs.writeFileSync(patchFp, stripKeysmithInsert(text), "utf8");
  } catch {
    /* no patch file */
  }
}

function main() {
  if (process.argv.includes("--uninstall")) {
    const dir = findProfileDir();
    if (!dir) {
      process.stderr.write("dsh-keysmith: no profile directory found\n");
      process.exit(1);
    }
    uninstallFromProfile(dir);
    process.stdout.write(`dsh-keysmith: uninstalled from ${dir}\n`);
    return;
  }

  const profileDir = findProfileDir();
  if (!profileDir) return;

  const fp = path.join(profileDir, "package.json");
  const pkg = readJson(fp);
  if (!pkg) {
    process.stderr.write(`dsh-keysmith: cannot read ${fp}\n`);
    process.exit(1);
  }
  pkg.dsh = pkg.dsh && typeof pkg.dsh === "object" ? pkg.dsh : {};
  pkg.dsh.profile = pkg.dsh.profile && typeof pkg.dsh.profile === "object" ? pkg.dsh.profile : {};
  const bundles = Array.isArray(pkg.dsh.profile.bundles) ? pkg.dsh.profile.bundles : [];
  if (!bundles.includes(NAME)) {
    pkg.dsh.profile.bundles = [...bundles, NAME];
    fs.writeFileSync(fp, `${JSON.stringify(pkg, null, 2)}\n`, "utf8");
    process.stdout.write(`dsh-keysmith: appended to bundles (${profileDir})\n`);
  } else {
    process.stdout.write(`dsh-keysmith: already in bundles (${profileDir})\n`);
  }

  try {
    ensureProfileInsert(profileDir);
  } catch (e) {
    process.stderr.write(`dsh-keysmith: insert failed: ${e && e.message ? e.message : e}\n`);
    process.exit(1);
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (invoked === fileURLToPath(import.meta.url)) main();
