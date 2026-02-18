import { api } from "@/lib/api";

export type LoginRequest = {
  email: string;
  password: string;
};

export type LoginResponse = {
  access: string;
  refresh?: string;
};

export async function login(values: LoginRequest): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/auth/login/", values);
  return res.data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout/");
}
