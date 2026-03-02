"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteAddress } from "@/lib/api/profile";
import type { AddressDto } from "@/lib/api/profile";
import { AddressDialog } from "./AddressDialog";

type Props = {
  addresses: AddressDto[];
};

export function AddressesCard({ addresses }: Props) {
  const router = useRouter();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<AddressDto | null>(null);
  const [busy, setBusy] = React.useState<number | null>(null);

  const openAdd = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (addr: AddressDto) => {
    setEditing(addr);
    setDialogOpen(true);
  };

  const onSaved = () => {
    setDialogOpen(false);
    router.refresh();
  };

  const onDelete = async (addr: AddressDto) => {
    if (!confirm(`Delete address "${addr.full_name} – ${addr.street_line_1}"?`))
      return;
    setBusy(addr.id);
    try {
      await deleteAddress(addr.id);
      toast.success("Address deleted.");
      router.refresh();
    } catch {
      toast.error("Failed to delete address.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Addresses</CardTitle>
          <Button size="sm" onClick={openAdd} data-testid="add-address-btn">
            Add address
          </Button>
        </CardHeader>
        <CardContent>
          {addresses.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No addresses saved yet.
            </p>
          ) : (
            <ul className="divide-y" data-testid="address-list">
              {addresses.map((addr) => (
                <li
                  key={addr.id}
                  className="flex items-start justify-between gap-4 py-3"
                  data-testid={`address-item-${addr.id}`}
                >
                  <div className="text-sm leading-snug">
                    <p className="font-medium">{addr.full_name}</p>
                    {addr.company ? (
                      <p className="text-muted-foreground">{addr.company}</p>
                    ) : null}
                    <p>{addr.street_line_1}</p>
                    {addr.street_line_2 ? <p>{addr.street_line_2}</p> : null}
                    <p>
                      {addr.postal_code} {addr.city}
                    </p>
                    <p className="uppercase">{addr.country}</p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Edit address"
                      onClick={() => openEdit(addr)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete address"
                      disabled={busy === addr.id}
                      onClick={() => onDelete(addr)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <AddressDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        initial={editing}
        onSaved={onSaved}
      />
    </>
  );
}
