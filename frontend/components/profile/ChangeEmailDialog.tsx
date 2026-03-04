/**
 * Dialog for initiating the secure email-change flow (ADR-035).
 *
 * Uses uncontrolled inputs (FormData on submit) per ADR-034 to avoid
 * hydration race conditions.
 *
 * Fields:
 *  - current_password  — required to prove account ownership
 *  - new_email         — the desired new address
 *  - new_email_confirm — repeated for typo prevention
 *
 * On success: toast confirmation and close the dialog.
 * On error:   toast error; field-level errors are displayed inline.
 */

"use client";

import * as React from "react";
import { toast } from "sonner";

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
import { requestEmailChange } from "@/lib/api/profile";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

type FieldErrors = {
  new_email?: string;
  new_email_confirm?: string;
  current_password?: string;
  non_field_errors?: string;
};

export function ChangeEmailDialog({ open, onOpenChange }: Props) {
  const [busy, setBusy] = React.useState(false);
  const [fieldErrors, setFieldErrors] = React.useState<FieldErrors>({});

  // Reset errors whenever the dialog is (re-)opened.
  React.useEffect(() => {
    if (open) setFieldErrors({});
  }, [open]);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFieldErrors({});

    // Collect values via FormData — uncontrolled inputs, no hydration risk.
    const data = new FormData(e.currentTarget);
    const newEmail = (data.get("new_email") as string).trim().toLowerCase();
    const newEmailConfirm = (data.get("new_email_confirm") as string)
      .trim()
      .toLowerCase();
    const currentPassword = data.get("current_password") as string;

    // Client-side mismatch check (mirrors BE validation for instant feedback).
    if (newEmail !== newEmailConfirm) {
      setFieldErrors({ new_email_confirm: "Email addresses do not match." });
      return;
    }

    setBusy(true);
    try {
      await requestEmailChange({
        new_email: newEmail,
        new_email_confirm: newEmailConfirm,
        current_password: currentPassword,
      });
      toast.success("Confirmation link sent to your new email.");
      onOpenChange(false);
    } catch (err: any) {
      // Map server-side field errors for inline display.
      const serverErrors: FieldErrors = {};
      const data = err?.response?.data;

      if (data?.errors) {
        if (data.errors.new_email) {
          serverErrors.new_email = data.errors.new_email[0];
        }
        if (data.errors.new_email_confirm) {
          serverErrors.new_email_confirm = data.errors.new_email_confirm[0];
        }
        if (data.errors.current_password) {
          serverErrors.current_password = data.errors.current_password[0];
        }
      }

      const topMessage =
        data?.message ||
        data?.detail ||
        err?.message ||
        "Failed to request email change.";

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
      <DialogContent className="max-w-sm" data-testid="change-email-dialog">
        <DialogHeader>
          <DialogTitle>Change email address</DialogTitle>
          <DialogDescription>
            Enter your new email address and current password. A confirmation
            link will be sent to the new address.
          </DialogDescription>
        </DialogHeader>

        {/* key remounts the form DOM on open/close so defaultValues reset cleanly. */}
        <form
          key={open ? "open" : "closed"}
          onSubmit={onSubmit}
          className="space-y-4"
          data-testid="change-email-form"
        >
          <div className="space-y-2">
            <Label htmlFor="new_email">New email</Label>
            <Input
              id="new_email"
              name="new_email"
              type="email"
              autoComplete="email"
              required
              defaultValue=""
              data-testid="input-new-email"
              aria-describedby={
                fieldErrors.new_email ? "new-email-error" : undefined
              }
            />
            {fieldErrors.new_email && (
              <p
                id="new-email-error"
                className="text-xs text-destructive"
                data-testid="error-new-email"
              >
                {fieldErrors.new_email}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="new_email_confirm">Confirm new email</Label>
            <Input
              id="new_email_confirm"
              name="new_email_confirm"
              type="email"
              autoComplete="email"
              required
              defaultValue=""
              data-testid="input-new-email-confirm"
              aria-describedby={
                fieldErrors.new_email_confirm
                  ? "new-email-confirm-error"
                  : undefined
              }
            />
            {fieldErrors.new_email_confirm && (
              <p
                id="new-email-confirm-error"
                className="text-xs text-destructive"
                data-testid="error-new-email-confirm"
              >
                {fieldErrors.new_email_confirm}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="current_password">Current password</Label>
            <Input
              id="current_password"
              name="current_password"
              type="password"
              autoComplete="current-password"
              required
              defaultValue=""
              data-testid="input-current-password"
              aria-describedby={
                fieldErrors.current_password
                  ? "current-password-error"
                  : undefined
              }
            />
            {fieldErrors.current_password && (
              <p
                id="current-password-error"
                className="text-xs text-destructive"
                data-testid="error-current-password"
              >
                {fieldErrors.current_password}
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
              data-testid="submit-change-email"
            >
              {busy ? "Sending…" : "Send confirmation"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
