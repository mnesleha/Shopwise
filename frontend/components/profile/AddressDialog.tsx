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

const EMPTY: AddressPayload = {
  full_name: "",
  street_line_1: "",
  street_line_2: "",
  city: "",
  postal_code: "",
  country: "",
  company: "",
  vat_id: "",
};

export function AddressDialog({ open, onOpenChange, initial, onSaved }: Props) {
  const [fields, setFields] = React.useState<AddressPayload>(EMPTY);
  const [busy, setBusy] = React.useState(false);

  // Populate form when dialog opens / switches mode
  React.useEffect(() => {
    if (open) {
      setFields(
        initial
          ? {
              full_name: initial.full_name,
              street_line_1: initial.street_line_1,
              street_line_2: initial.street_line_2,
              city: initial.city,
              postal_code: initial.postal_code,
              country: initial.country,
              company: initial.company,
              vat_id: initial.vat_id,
            }
          : EMPTY,
      );
    }
  }, [open, initial]);

  const set =
    (key: keyof AddressPayload) => (e: React.ChangeEvent<HTMLInputElement>) =>
      setFields((prev) => ({ ...prev, [key]: e.target.value }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);

    try {
      if (initial) {
        await updateAddress(initial.id, fields);
        toast.success("Address updated.");
      } else {
        await createAddress(fields);
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

        <form
          onSubmit={onSubmit}
          className="space-y-3"
          data-testid="address-form"
        >
          <Field
            label="Full name"
            id="full_name"
            value={fields.full_name}
            onChange={set("full_name")}
            required
          />
          <Field
            label="Company (optional)"
            id="company"
            value={fields.company}
            onChange={set("company")}
          />
          <Field
            label="Street"
            id="street_line_1"
            value={fields.street_line_1}
            onChange={set("street_line_1")}
            required
          />
          <Field
            label="Apt / floor (optional)"
            id="street_line_2"
            value={fields.street_line_2}
            onChange={set("street_line_2")}
          />
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Postal code"
              id="postal_code"
              value={fields.postal_code}
              onChange={set("postal_code")}
              required
            />
            <Field
              label="City"
              id="city"
              value={fields.city}
              onChange={set("city")}
              required
            />
          </div>
          <Field
            label="Country (ISO 2-letter)"
            id="country"
            value={fields.country}
            onChange={set("country")}
            required
            maxLength={2}
            placeholder="CZ"
          />
          <Field
            label="VAT ID (optional)"
            id="vat_id"
            value={fields.vat_id}
            onChange={set("vat_id")}
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
