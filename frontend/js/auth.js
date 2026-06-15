const AUTH_STORAGE_KEY = "mac_ai_auth";

export function getStoredAuth() {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function storeAuth(data) {
  sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data));
}

export function clearAuth() {
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
}

export function getAccessToken() {
  const auth = getStoredAuth();
  return auth?.access_token || null;
}

export async function login(username, password) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Login fallito");
  }
  storeAuth(data);
  return data;
}

export async function logout() {
  const token = getAccessToken();
  if (token) {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  }
  clearAuth();
}

export async function fetchCurrentUser() {
  const token = getAccessToken();
  if (!token) {
    return null;
  }
  const response = await fetch("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    clearAuth();
    return null;
  }
  return response.json();
}

export function authHeaders(extra = {}) {
  const token = getAccessToken();
  const headers = { ...extra };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}
