"use client";

import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { createAddress, updateAddress } from "@/lib/api/profile";
import type { AddressDto, AddressPayload } from "@/lib/api/profile";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** null = create mode, non-null = edit mode */
  initial: AddressDto | null;
  onSaved: () => void;
};

export function AddressDialog({ open, onOpenChange, initial, onSaved }: Props) {
  const [busy, setBusy] = React.useState(false);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // Collect values via FormData — no controlled state, no hydration risk.
    const data = new FormData(e.currentTarget);
    const payload: AddressPayload = {
      full_name: (data.get("full_name") as string).trim(),
      street_line_1: (data.get("street_line_1") as string).trim(),
      street_line_2: (data.get("street_line_2") as string).trim(),
      city: (data.get("city") as string).trim(),
      postal_code: (data.get("postal_code") as string).trim(),
      country: (data.get("country") as string).trim(),
      company: (data.get("company") as string).trim(),
      vat_id: (data.get("vat_id") as string).trim(),
    };

    setBusy(true);
    try {
      if (initial) {
        await updateAddress(initial.id, payload);
        toast.success("Address updated.");
      } else {
        await createAddress(payload);
        toast.success("Address added.");
      }
      onSaved();
    } catch {
      toast.error("Failed to save address.");
    } finally {
      setBusy(false);
    }
  };

  const isEdit = initial !== null;
  const title = isEdit ? "Edit address" : "Add address";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="address-dialog">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        {/* key remounts the form DOM when switching create↔edit or reopening,
            so defaultValues are re-applied cleanly without controlled state. */}
        <form
          key={open ? (initial?.id ?? "new") : "closed"}
          onSubmit={onSubmit}
          className="space-y-3"
          data-testid="address-form"
        >
          <Field
            label="Full name"
            id="full_name"
            defaultValue={initial?.full_name ?? ""}
            required
          />
          <Field
            label="Company (optional)"
            id="company"
            defaultValue={initial?.company ?? ""}
          />
          <Field
            label="Street"
            id="street_line_1"
            defaultValue={initial?.street_line_1 ?? ""}
            required
          />
          <Field
            label="Apt / floor (optional)"
            id="street_line_2"
            defaultValue={initial?.street_line_2 ?? ""}
          />
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Postal code"
              id="postal_code"
              defaultValue={initial?.postal_code ?? ""}
              required
            />
            <Field
              label="City"
              id="city"
              defaultValue={initial?.city ?? ""}
              required
            />
          </div>
          <Field
            label="Country (ISO 2-letter)"
            id="country"
            defaultValue={initial?.country ?? ""}
            required
            maxLength={2}
            placeholder="CZ"
          />
          <Field
            label="VAT ID (optional)"
            id="vat_id"
            defaultValue={initial?.vat_id ?? ""}
          />

          <DialogFooter className="pt-2">
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
              data-testid="address-dialog-submit"
            >
              {busy ? "Saving…" : isEdit ? "Save changes" : "Add address"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── small helper ─────────────────────────────────────────────────────────────

function Field({
  label,
  id,
  ...rest
}: {
  label: string;
  id: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} name={id} {...rest} />
    </div>
  );
}
