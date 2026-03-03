"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
  /** Address staged for deletion; drives the confirm AlertDialog. */
  const [pendingDelete, setPendingDelete] = React.useState<AddressDto | null>(null);

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

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const addr = pendingDelete;
    setPendingDelete(null);
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
                    <p className="font-medium">{addr.first_name} {addr.last_name}</p>
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
                      onClick={() => setPendingDelete(addr)}
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

      {/* Confirmation dialog for address deletion */}
      <AlertDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => { if (!open) setPendingDelete(null); }}
      >
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete address?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete && (
                <>
                  <span className="font-medium">
                    {pendingDelete.first_name} {pendingDelete.last_name}
                  </span>
                  {" — "}
                  {pendingDelete.street_line_1}, {pendingDelete.city}
                </>
              )}
              <br />
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
