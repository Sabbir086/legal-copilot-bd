export type AuthUser = { id: string; email: string };
export type AuthSession = {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  expires_at?: number;
  user: AuthUser;
};

const STORAGE_KEY = "legal-copilot-auth-session";
const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL || "").replace(/\/$/, "");
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export function getSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (!value) return null;
    const parsed = JSON.parse(value) as AuthSession;
    return parsed.access_token && parsed.user?.id ? parsed : null;
  } catch {
    return null;
  }
}

export function saveSession(session: AuthSession) {
  const next = { ...session, expires_at: session.expires_at || (session.expires_in ? Math.floor(Date.now() / 1000) + session.expires_in : undefined) };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function clearSession() {
  window.localStorage.removeItem(STORAGE_KEY);
}

export async function getValidSession(): Promise<AuthSession | null> {
  const session = getSession();
  if (!session) return null;
  if (!session.expires_at || session.expires_at * 1000 > Date.now() + 90_000) return session;
  if (!session.refresh_token) { clearSession(); return null; }
  try {
    const refreshed = await authRequest<AuthSession>("token?grant_type=refresh_token", { refresh_token: session.refresh_token });
    const next = { ...session, ...refreshed };
    saveSession(next);
    return next;
  } catch {
    clearSession();
    return null;
  }
}

export async function signOut() {
  const session = getSession();
  try {
    if (session?.access_token) await authRequest("logout", {}, "POST", session.access_token);
  } finally {
    clearSession();
  }
}

async function authRequest<T>(path: string, body: Record<string, unknown>, method = "POST", accessToken?: string): Promise<T> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error("NEXT_PUBLIC_SUPABASE_URL এবং NEXT_PUBLIC_SUPABASE_ANON_KEY frontend/.env.local-এ সেট করুন।");
  }
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    apikey: SUPABASE_ANON_KEY,
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const response = await fetch(`${SUPABASE_URL}/auth/v1/${path}`, {
    method,
    headers,
    body: method === "GET" ? undefined : JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.msg || payload.message || payload.error_description || payload.error || `Supabase Auth error (${response.status})`);
  }
  return payload as T;
}

export async function signIn(email: string, password: string) {
  return authRequest<AuthSession>("token?grant_type=password", { email: email.trim().toLowerCase(), password });
}

export async function signUp(email: string, password: string) {
  return authRequest<AuthSession>("signup", { email: email.trim().toLowerCase(), password });
}

export async function requestPasswordReset(email: string, redirectTo: string) {
  return authRequest<{ message?: string }>(`recover?redirect_to=${encodeURIComponent(redirectTo)}`, { email: email.trim().toLowerCase() });
}

export async function updatePassword(accessToken: string, password: string) {
  return authRequest<AuthUser>("user", { password }, "PUT", accessToken);
}

export async function getBackendUser(accessToken: string) {
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
  const response = await fetch(`${apiBase}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Account profile লোড করা যায়নি।");
  return payload.user as AuthUser & { role: "user" | "admin" | "super_admin"; is_active: boolean };
}

export async function bootstrapSuperAdmin(email: string, password: string) {
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
  const response = await fetch(`${apiBase}/api/v1/auth/bootstrap-super-admin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Super Admin bootstrap failed");
  return payload;
}
