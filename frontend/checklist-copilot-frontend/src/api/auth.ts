import { apiRequest } from './http'
import type { AuthResponse, LoginRequest } from '../types/auth'
import type { User } from '../types/user'
import { saveToken } from '../auth/tokenStorage'

export async function login(payload: LoginRequest): Promise<AuthResponse> {
  const response = await apiRequest<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

  saveToken(response.access_token)
  return response
}

export function getCurrentUser(token?: string): Promise<User> {
  return apiRequest<User>('/auth/me', { method: 'GET' }, token)
}
