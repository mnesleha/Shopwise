import { api } from "@/lib/api";

export type LoginRequest = {
  email: string;
  password: string;
  /** When true, the backend issues a long-lived refresh token ("remember me"). */
  remember_me?: boolean;
};

export type LoginResponse = {
  access: string;
  refresh?: string;
};

export type MeResponse = {
  is_authenticated: boolean;
  id?: number;
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  email_verified?: boolean;
};

export type RegisterRequest = {
  email: string;
  password: string;
};

export type RegisterResponse = {
  is_authenticated: boolean;
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  email_verified: boolean;
};

export type VerifyEmailResponse = {
  email_verified: boolean;
  claimed_orders: number;
};

export async function login(values: LoginRequest): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/auth/login/", values);
  return res.data;
}

export async function requestEmailVerification(email: string): Promise<void> {
  await api.post("/auth/request-email-verification/", { email });
}

export async function verifyEmail(token: string): Promise<VerifyEmailResponse> {
  const resp = await api.post<VerifyEmailResponse>("/auth/verify-email/", {
    token,
  });
  return resp.data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout/");
}

export async function register(
  values: RegisterRequest,
): Promise<RegisterResponse> {
  const res = await api.post<RegisterResponse>("/auth/register/", values);
  return res.data;
}

/** Initiate a password-reset flow (anti-enumeration: always 204). */
export async function requestPasswordReset(email: string): Promise<void> {
  await api.post("/auth/password-reset/request/", { email });
}

/** Confirm a password reset with the single-use token from email. */
export async function confirmPasswordReset(payload: {
  token: string;
  new_password: string;
  new_password_confirm: string;
}): Promise<void> {
  await api.post("/auth/password-reset/confirm/", payload);
}

// ---------------------------------------------------------------------------
// Guest-order bootstrap
// ---------------------------------------------------------------------------

export type GuestBootstrapRequest = {
  password: string;
  password_confirm: string;
};

export type GuestBootstrapResponse = {
  is_authenticated: boolean;
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  email_verified: boolean;
};

/**
 * Convert a verified guest order into a full account.
 *
 * Requires the same token that was used to view the guest order.
 * On success the backend sets JWT auth cookies; call `auth.refresh()` to
 * synchronise the frontend auth state.
 */
export async function bootstrapGuestAccount(
  orderId: number | string,
  token: string,
  payload: GuestBootstrapRequest,
): Promise<GuestBootstrapResponse> {
  const res = await api.post<GuestBootstrapResponse>(
    `/guest/orders/${orderId}/bootstrap/?token=${encodeURIComponent(token)}`,
    payload,
  );
  return res.data;
}
