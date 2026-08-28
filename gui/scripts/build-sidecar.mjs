// PyInstaller onefile sidecar 构建（仅本机原生目标）。
// dsh-keysmith.py 将 prompt 内嵌于源码，无 sys.executable 自重调用；
// 若日后加入自重调用，必须同时带 getattr(sys, "frozen") 判断。
import { chmodSync, copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const guiDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoDir = resolve(guiDir, "..");
const sourcePath = join(repoDir, "dsh-keysmith.py");
const expectedCliVersion = readFileSync(join(repoDir, "VERSION"), "utf8").trim();

const TARGETS = {
  "aarch64-apple-darwin": { platform: "darwin", arch: "arm64", extension: "" },
  "x86_64-pc-windows-msvc": { platform: "win32", arch: "x64", extension: ".exe" },
};

function argument(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? null : process.argv[index + 1];
}

function hostTarget() {
  if (process.platform === "darwin" && process.arch === "arm64") return "aarch64-apple-darwin";
  if (process.platform === "win32" && process.arch === "x64") return "x86_64-pc-windows-msvc";
  throw new Error(`Unsupported native build host: ${process.platform}/${process.arch}`);
}

const target = argument("--target") || process.env.TAURI_ENV_TARGET_TRIPLE || hostTarget();
const targetConfig = TARGETS[target];
if (!targetConfig) throw new Error(`Unsupported target: ${target}`);
if (process.platform !== targetConfig.platform || process.arch !== targetConfig.arch) {
  throw new Error(`PyInstaller sidecars must be built natively: ${target} requires ${targetConfig.platform}/${targetConfig.arch}`);
}
if (!existsSync(sourcePath)) throw new Error(`CLI source not found: ${sourcePath}`);

const source = readFileSync(sourcePath, "utf8");
const selfReinvoke = /sys\.executable[\s\S]{0,120}Path\(__file__\)/;
if (selfReinvoke.test(source) && !source.includes('getattr(sys, "frozen"')) {
  throw new Error("dsh-keysmith.py self-reinvoke is not frozen-aware; refusing to package");
}

const buildRoot = join(guiDir, "src-tauri", "target", "sidecar-build", target);
const distDir = join(buildRoot, "dist");
const workDir = join(buildRoot, "work");
const specDir = join(buildRoot, "spec");
mkdirSync(buildRoot, { recursive: true });
rmSync(distDir, { recursive: true, force: true });
rmSync(workDir, { recursive: true, force: true });
rmSync(specDir, { recursive: true, force: true });

const python = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
const pythonEnv = { ...process.env, PYTHONNOUSERSITE: "1" };
delete pythonEnv.PYTHONHOME;
delete pythonEnv.PYTHONPATH;
delete pythonEnv.PYTHONUSERBASE;

const result = spawnSync(
  python,
  [
    "-m",
    "PyInstaller",
    "--clean",
    "--noconfirm",
    "--onefile",
    "--name",
    "dsh-keysmith-cli",
    "--distpath",
    distDir,
    "--workpath",
    workDir,
    "--specpath",
    specDir,
    sourcePath,
  ],
  { cwd: guiDir, encoding: "utf8", stdio: "inherit", env: pythonEnv },
);
if (result.error) throw result.error;
if (result.status !== 0) {
  throw new Error(`PyInstaller failed with exit code ${result.status}. Install gui/requirements-build.txt in the active Python environment.`);
}

const builtPath = join(distDir, `dsh-keysmith-cli${targetConfig.extension}`);
if (!existsSync(builtPath)) throw new Error(`PyInstaller output missing: ${builtPath}`);

const binariesDir = join(guiDir, "src-tauri", "binaries");
const destination = join(binariesDir, `dsh-keysmith-cli-${target}${targetConfig.extension}`);
const temporary = `${destination}.tmp-${process.pid}`;
mkdirSync(binariesDir, { recursive: true });
copyFileSync(builtPath, temporary);
if (process.platform !== "win32") chmodSync(temporary, 0o755);
renameSync(temporary, destination);

const smoke = spawnSync(destination, ["--version"], { encoding: "utf8" });
if (smoke.error) throw smoke.error;
const reportedVersion = smoke.stdout.trim().split(/\s+/).at(-1);
if (smoke.status !== 0 || reportedVersion !== expectedCliVersion) {
  throw new Error(`Frozen sidecar version smoke failed: ${smoke.stderr || smoke.stdout}`);
}

const smokeHome = mkdtempSync(join(tmpdir(), "dsh-keysmith-smoke-"));
const statusSmoke = spawnSync(destination, ["--status", "--json", "--dsh-dir", smokeHome], { encoding: "utf8" });
if (statusSmoke.error) throw statusSmoke.error;
if (statusSmoke.status !== 0 || !statusSmoke.stdout.includes('"schema": "dsh-keysmith/v1"')) {
  throw new Error(`Frozen sidecar --status --json smoke failed: ${statusSmoke.stderr || statusSmoke.stdout}`);
}
rmSync(smokeHome, { recursive: true, force: true });

console.log(`Built ${destination}`);
