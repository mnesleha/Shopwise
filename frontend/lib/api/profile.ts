import { api } from "@/lib/api";

// ── DTOs ─────────────────────────────────────────────────────────────────────

export type ProfileDto = {
  id: number;
  default_shipping_address: number | null;
  default_billing_address: number | null;
};

export type AddressDto = {
  id: number;
  full_name: string;
  street_line_1: string;
  street_line_2: string;
  city: string;
  postal_code: string;
  country: string;
  company: string;
  vat_id: string;
};

export type AddressPayload = Omit<AddressDto, "id">;

// ── Profile ───────────────────────────────────────────────────────────────────

export async function getProfile(): Promise<ProfileDto> {
  const res = await api.get<ProfileDto>("/profile/");
  return res.data;
}

export async function updateProfile(
  patch: Partial<
    Pick<ProfileDto, "default_shipping_address" | "default_billing_address">
  >,
): Promise<ProfileDto> {
  const res = await api.patch<ProfileDto>("/profile/", patch);
  return res.data;
}

// ── Addresses ─────────────────────────────────────────────────────────────────

export async function listAddresses(): Promise<AddressDto[]> {
  const res = await api.get<AddressDto[]>("/addresses/");
  return res.data;
}

export async function createAddress(
  payload: AddressPayload,
): Promise<AddressDto> {
  const res = await api.post<AddressDto>("/addresses/", payload);
  return res.data;
}

export async function updateAddress(
  id: number,
  payload: Partial<AddressPayload>,
): Promise<AddressDto> {
  const res = await api.patch<AddressDto>(`/addresses/${id}/`, payload);
  return res.data;
}

export async function deleteAddress(id: number): Promise<void> {
  await api.delete(`/addresses/${id}/`);
}
