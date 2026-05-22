import { apiRequest } from "./http";
import type {
  User,
  UserCreateRequest,
  UserCreateResponse,
  UserDeleteResponse,
  UserListResponse,
} from "../types/user";

export function registerUser(payload: UserCreateRequest): Promise<UserCreateResponse> {
  return apiRequest<UserCreateResponse>("/users/create", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listUsers(): Promise<UserListResponse> {
  return apiRequest<UserListResponse>("/users", { method: "GET" });
}

export function getUserById(userId: string): Promise<User> {
  return apiRequest<User>(`/users/${userId}`, { method: "GET" });
}

export function deleteUser(userId: string): Promise<UserDeleteResponse> {
  return apiRequest<UserDeleteResponse>(`/users/delete/${userId}`, { method: "DELETE" });
}
