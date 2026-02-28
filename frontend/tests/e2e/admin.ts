import { execFileSync } from "node:child_process";
import path from "node:path";
import fs from "node:fs";
import dotenv from "dotenv";

export async function adminCancelOrder(orderId: number) {
  // Adjust this to your backend folder location
  const backendDir =
    process.env.BACKEND_DIR ?? path.resolve(process.cwd(), ".", "backend");

  const python =
    process.env.PYTHON ??
    path.join(backendDir, "..", "venv", "Scripts", "python.exe");

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

  console.log("Backend dir:", backendDir);
  console.log("Using python:", python);

  const script = `
from orders.models import Order
o = Order.objects.get(pk=${orderId})
o.status = "CANCELLED"
# if your model has these fields, set them too; otherwise remove:
if hasattr(o, "cancelled_by"):
    o.cancelled_by = "ADMIN"
if hasattr(o, "cancel_reason"):
    o.cancel_reason = "ADMIN_CANCELLED"
o.save()
print("OK")
`.trim();

  execFileSync(python, [managePy, "shell", "-c", script], {
    cwd: backendDir,
    stdio: "inherit",
    env: env,
  });
}
