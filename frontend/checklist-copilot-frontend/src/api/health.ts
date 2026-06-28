import { apiRequest } from './http'

export type HealthResponse = {
  status: string
}

// Pings the backend health endpoint so a sleeping Render instance can start before users log in.
export function pingBackendHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health', { method: 'GET' })
}
