import { Badge } from "@/components/ui/badge"

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  CREATED: { label: "Created", variant: "outline" },
  PAID: { label: "Paid", variant: "default" },
  SHIPPED: { label: "Shipped", variant: "secondary" },
  DELIVERED: { label: "Delivered", variant: "default" },
  CANCELLED: { label: "Cancelled", variant: "destructive" },
}

interface OrderStatusBadgeProps {
  status: string
}

export function OrderStatusBadge({ status }: OrderStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    variant: "outline" as const,
  }

  return <Badge variant={config.variant}>{config.label}</Badge>
}
