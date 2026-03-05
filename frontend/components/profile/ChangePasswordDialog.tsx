/**
 * Dialog for changing the account password.
 *
 * Uses uncontrolled inputs (FormData on submit) per ADR-034 to avoid
 * hydration race conditions with controlled React inputs.
 *
 * Fields:
 *  - current_password      — required to prove account ownership
 *  - new_password          — the desired new password
 *  - new_password_confirm  — repeated for typo prevention
 *
 * On success: toast notification and redirect to /login?passwordChanged=1.
 *             The server has already revoked all sessions (token_version++).
 * On error:   toast error; field-level errors are displayed inline.
 */

"use client";

import * as React from "react";
import { flushSync } from "react-dom";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { changePassword } from "@/lib/api/profile";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

type FieldErrors = {
  current_password?: string;
  new_password?: string | string[];
  new_password_confirm?: string;
};

export function ChangePasswordDialog({ open, onOpenChange }: Props) {
  const router = useRouter();
  const { setAnonymous } = useAuth();
  const { resetCount } = useCart();
  const [busy, setBusy] = React.useState(false);
  const [fieldErrors, setFieldErrors] = React.useState<FieldErrors>({});
  const [showCurrent, setShowCurrent] = React.useState(false);
  const [showNew, setShowNew] = React.useState(false);
  const [showConfirm, setShowConfirm] = React.useState(false);

  // Reset errors and show-password toggles whenever the dialog is (re-)opened.
  React.useEffect(() => {
    if (open) {
      setFieldErrors({});
      setShowCurrent(false);
      setShowNew(false);
      setShowConfirm(false);
    }
  }, [open]);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFieldErrors({});

    // Collect values via FormData — uncontrolled inputs, no hydration risk.
    const formData = new FormData(e.currentTarget);
    const currentPassword = formData.get("current_password") as string;
    const newPassword = formData.get("new_password") as string;
    const newPasswordConfirm = formData.get("new_password_confirm") as string;

    // Client-side mismatch check (mirrors BE validation for instant feedback).
    if (newPassword !== newPasswordConfirm) {
      setFieldErrors({ new_password_confirm: "Passwords do not match." });
      return;
    }

    setBusy(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      });

      // Synchronously commit the anonymous + empty-cart state to the DOM
      // before router.push starts its concurrent transition. Without flushSync,
      // React 18 batches these setState calls into the transition and the
      // header stays authenticated / badge stays stale until the new page
      // settles (same fix as the logout button in HeaderAuthClient).
      flushSync(() => {
        setAnonymous();
        resetCount(); // zero cart badge immediately; avoids stale account-cart count
      });
      // The login page shows the success toast via ?passwordChanged=1.
      router.push("/login?passwordChanged=1");
    } catch (err: any) {
      // Map server-side field errors for inline display.
      const serverErrors: FieldErrors = {};
      const body = err?.response?.data;

      if (body?.errors) {
        if (body.errors.current_password) {
          serverErrors.current_password = body.errors.current_password[0];
        }
        if (body.errors.new_password) {
          serverErrors.new_password = Array.isArray(body.errors.new_password)
            ? body.errors.new_password[0]
            : body.errors.new_password;
        }
        if (body.errors.new_password_confirm) {
          serverErrors.new_password_confirm =
            body.errors.new_password_confirm[0];
        }
      }

      const topMessage =
        body?.message ||
        body?.detail ||
        err?.message ||
        "Failed to change password.";

      if (Object.keys(serverErrors).length > 0) {
        setFieldErrors(serverErrors);
      }

      toast.error(String(topMessage));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm" data-testid="change-password-dialog">
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>
            Enter your current password and choose a new one. All active
            sessions will be signed out after the change.
          </DialogDescription>
        </DialogHeader>

        {/*
          key remounts the form DOM on open/close so defaultValues reset
          cleanly — the uncontrolled inputs are wiped without setting state.
        */}
        <form
          key={open ? "open" : "closed"}
          onSubmit={onSubmit}
          className="space-y-4"
          data-testid="change-password-form"
        >
          {/* ── current_password ─────────────────────────────────────── */}
          <div className="space-y-2">
            <Label htmlFor="cp_current_password">Current password</Label>
            <div className="relative">
              <Input
                id="cp_current_password"
                name="current_password"
                type={showCurrent ? "text" : "password"}
                autoComplete="current-password"
                required
                defaultValue=""
                className="pr-10"
                data-testid="input-current-password"
                aria-describedby={
                  fieldErrors.current_password
                    ? "cp-current-password-error"
                    : undefined
                }
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground"
                onClick={() => setShowCurrent((v) => !v)}
                tabIndex={-1}
                aria-label={showCurrent ? "Hide password" : "Show password"}
              >
                {showCurrent ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {fieldErrors.current_password && (
              <p
                id="cp-current-password-error"
                className="text-sm text-destructive"
                data-testid="error-current-password"
              >
                {fieldErrors.current_password}
              </p>
            )}
          </div>

          {/* ── new_password ─────────────────────────────────────────── */}
          <div className="space-y-2">
            <Label htmlFor="cp_new_password">New password</Label>
            <div className="relative">
              <Input
                id="cp_new_password"
                name="new_password"
                type={showNew ? "text" : "password"}
                autoComplete="new-password"
                required
                defaultValue=""
                className="pr-10"
                data-testid="input-new-password"
                aria-describedby={
                  fieldErrors.new_password ? "cp-new-password-error" : undefined
                }
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground"
                onClick={() => setShowNew((v) => !v)}
                tabIndex={-1}
                aria-label={showNew ? "Hide password" : "Show password"}
              >
                {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {fieldErrors.new_password && (
              <p
                id="cp-new-password-error"
                className="text-sm text-destructive"
                data-testid="error-new-password"
              >
                {Array.isArray(fieldErrors.new_password)
                  ? fieldErrors.new_password.join(" ")
                  : fieldErrors.new_password}
              </p>
            )}
          </div>

          {/* ── new_password_confirm ─────────────────────────────────── */}
          <div className="space-y-2">
            <Label htmlFor="cp_new_password_confirm">
              Confirm new password
            </Label>
            <div className="relative">
              <Input
                id="cp_new_password_confirm"
                name="new_password_confirm"
                type={showConfirm ? "text" : "password"}
                autoComplete="new-password"
                required
                defaultValue=""
                className="pr-10"
                data-testid="input-new-password-confirm"
                aria-describedby={
                  fieldErrors.new_password_confirm
                    ? "cp-new-password-confirm-error"
                    : undefined
                }
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground"
                onClick={() => setShowConfirm((v) => !v)}
                tabIndex={-1}
                aria-label={showConfirm ? "Hide password" : "Show password"}
              >
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {fieldErrors.new_password_confirm && (
              <p
                id="cp-new-password-confirm-error"
                className="text-sm text-destructive"
                data-testid="error-new-password-confirm"
              >
                {fieldErrors.new_password_confirm}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={busy}
              data-testid="submit-change-password-btn"
            >
              {busy ? "Saving…" : "Change password"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
