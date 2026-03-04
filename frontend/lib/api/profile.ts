import { api } from "@/lib/api";

// ── DTOs ─────────────────────────────────────────────────────────────────────

export type AccountDto = {
  email: string;
  first_name: string;
  last_name: string;
};

export type AccountPatch = Pick<AccountDto, "first_name" | "last_name">;

export type ProfileDto = {
  id: number;
  default_shipping_address: number | null;
  default_billing_address: number | null;
};

export type AddressDto = {
  id: number;
  first_name: string;
  last_name: string;
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

// ── Account ───────────────────────────────────────────────────────────────────

export async function getAccount(): Promise<AccountDto> {
  const res = await api.get<AccountDto>("/account/");
  return res.data;
}

export async function patchAccount(data: AccountPatch): Promise<AccountDto> {
  const res = await api.patch<AccountDto>("/account/", data);
  return res.data;
}

/** Payload for POST /api/v1/account/change-email/ */
export type ChangeEmailPayload = {
  new_email: string;
  new_email_confirm: string;
  current_password: string;
};

/**
 * Initiate the email-change flow.
 * Returns void on 204 success; throws on validation / auth errors.
 */
export async function requestEmailChange(
  payload: ChangeEmailPayload,
): Promise<void> {
  await api.post("/account/change-email/", payload);
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
