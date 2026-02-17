import { api } from "@/lib/api";
import type { CheckoutValues } from "@/components/checkout/CheckoutForm";
import type { OrderDto } from "@/lib/api/orders";

export async function checkoutCart(values: CheckoutValues): Promise<OrderDto> {
  const payload = {
    customer_email: values.customer_email,

    shipping_name: values.shipping_name,
    shipping_address_line1: values.shipping_address_line1,
    shipping_address_line2: values.shipping_address_line2,
    shipping_city: values.shipping_city,
    shipping_postal_code: values.shipping_postal_code,
    shipping_country: values.shipping_country,
    shipping_phone: values.shipping_phone,

    billing_same_as_shipping: values.billing_same_as_shipping,

    ...(values.billing_same_as_shipping
      ? {}
      : {
          billing_name: values.billing_name,
          billing_address_line1: values.billing_address_line1,
          billing_address_line2: values.billing_address_line2,
          billing_city: values.billing_city,
          billing_postal_code: values.billing_postal_code,
          billing_country: values.billing_country,
          billing_phone: values.billing_phone,
        }),
  };

  const res = await api.post<OrderDto>("/cart/checkout/", payload);
  return res.data;
}
