import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, readFileSync, rmSync } from "node:fs";
import path from "node:path";

function backendPython(): string {
  if (process.env.E2E_PYTHON) return process.env.E2E_PYTHON;
  const root = path.resolve(__dirname, "..", "backend", ".venv");
  const windows = path.join(root, "Scripts", "python.exe");
  return existsSync(windows) ? windows : path.join(root, "bin", "python");
}

// Stops the stack and deletes the throwaway database, which removes every user the tests created.
export default async function globalTeardown() {
  const pidFile = path.join(__dirname, ".logs", "stack.pid");
  if (existsSync(pidFile)) {
    const pid = readFileSync(pidFile, "utf8").trim();
    try {
      if (process.platform === "win32") execFileSync("taskkill", ["/PID", pid, "/T", "/F"], { stdio: "ignore" });
      else process.kill(-Number(pid));
    } catch {
      // already gone
    }
    rmSync(pidFile, { force: true });
  }
  const result = spawnSync(backendPython(), ["stack.py", "--cleanup"], { cwd: __dirname, encoding: "utf8" });
  console.log((result.stdout || result.stderr || "").trim());
}
