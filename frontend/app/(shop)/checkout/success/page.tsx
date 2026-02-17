export default function CheckoutSuccessPage() {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Order created</h1>
      <p className="text-muted-foreground">
        If you checked out as a guest, we sent you an order access link by email.
      </p>
      <p className="text-muted-foreground">
        If you are signed in, you can view your order in the Orders section.
      </p>
    </div>
  );
}
