const ACCESS_TOKEN_KEY = "access_token";

export function saveToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function removeToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}
