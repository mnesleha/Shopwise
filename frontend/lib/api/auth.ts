import { api } from "@/lib/api";

export type LoginRequest = {
  email: string;
  password: string;
};

export type LoginResponse = {
  access: string;
  refresh?: string;
  cart_merge?: {
    performed: boolean;
    warnings?: Array<any>;
    discount_decision?: any;
  };
  claimed_orders?: number;
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

export async function login(values: LoginRequest): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/auth/login/", values);
  return res.data;
}

export async function requestEmailVerification(email: string): Promise<void> {
  await api.post("/auth/request-email-verification/", { email });
}

export type VerifyEmailResponse = {
  email_verified: boolean;
  claimed_orders: number;
};

export async function verifyEmail(token: string): Promise<VerifyEmailResponse> {
  const resp = await api.post<VerifyEmailResponse>("/auth/verify-email/", {
    token,
  });
  return resp.data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout/");
}
