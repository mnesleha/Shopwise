// frontend/tests/e2e/helpers/backend-db.ts
import path from "node:path";
import { execFileSync } from "node:child_process";
import dotenv from "dotenv";
import fs from "node:fs";

function getBackendDir(): string {
  return process.env.BACKEND_DIR ?? path.resolve(process.cwd(), ".", "backend");
}

function getPythonExe(backendDir: string): string {
  return (
    process.env.PYTHON ??
    path.join(backendDir, "..", "venv", "Scripts", "python.exe")
  );
}

export function setUserEmailVerified(email: string, verified: boolean) {
  const backendDir = getBackendDir();
  const python = getPythonExe(backendDir);

  // Load backend env file
  const envFile =
    process.env.BACKEND_ENV_FILE ?? path.join(backendDir, ".env.dev");

  if (!fs.existsSync(envFile)) {
    throw new Error(`Backend env file not found: ${envFile}`);
  }

  const parsed = dotenv.parse(fs.readFileSync(envFile));

  // Merge env: current process env + backend .env.dev
  // backend file wins (so it's explicit and deterministic)
  const env = { ...process.env, ...parsed };

  const managePy = path.join(backendDir, "manage.py");

  const script = `
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(email="${email}")
u.email_verified = ${verified ? "True" : "False"}
u.save(update_fields=["email_verified"])
print("OK")
`.trim();

  execFileSync(python, ["manage.py", "shell", "-c", script], {
    cwd: backendDir,
    stdio: "inherit",
    env,
  });
}
