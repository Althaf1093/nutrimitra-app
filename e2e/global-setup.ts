import { spawn } from "node:child_process";
import { existsSync, mkdirSync, openSync, writeFileSync } from "node:fs";
import path from "node:path";

const API = process.env.E2E_API_URL || "http://localhost:8101";
const WEB = `http://localhost:${process.env.E2E_WEB_PORT || "8102"}`;

function backendPython(): string {
  if (process.env.E2E_PYTHON) return process.env.E2E_PYTHON;
  const root = path.resolve(__dirname, "..", "backend", ".venv");
  const windows = path.join(root, "Scripts", "python.exe");
  return existsSync(windows) ? windows : path.join(root, "bin", "python");
}

async function waitFor(url: string, name: string, seconds: number) {
  const deadline = Date.now() + seconds * 1000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`${name} did not come up at ${url}. See e2e/.logs for details.`);
}

// Starts the whole stack (fake AI, backend on its own database, web build) and leaves it running for the tests.
export default async function globalSetup() {
  mkdirSync(path.join(__dirname, ".logs"), { recursive: true });
  mkdirSync(path.join(__dirname, "screenshots"), { recursive: true });
  const log = openSync(path.join(__dirname, ".logs", "stack.log"), "w");
  const stack = spawn(backendPython(), ["stack.py", ...(process.env.E2E_REBUILD ? ["--rebuild"] : [])], {
    cwd: __dirname,
    detached: true,
    stdio: ["ignore", log, log],
    windowsHide: true,
  });
  stack.unref();
  writeFileSync(path.join(__dirname, ".logs", "stack.pid"), String(stack.pid));
  // The first run builds the web app, which takes a few minutes.
  await waitFor(`${API}/api/`, "the backend", 600);
  await waitFor(`${WEB}/`, "the web app", 60);
}
