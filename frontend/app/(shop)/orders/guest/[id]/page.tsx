export default function GuestOrderPage({ params }: { params: { id: string } }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Guest order</h1>
      <p className="text-muted-foreground">Order ID: {params.id}</p>
    </div>
  );
}
