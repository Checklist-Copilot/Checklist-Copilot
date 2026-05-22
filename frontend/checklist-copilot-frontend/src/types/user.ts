export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export interface UserCreateRequest {
  username: string;
  email: string;
  password: string;
}

export interface UserCreateResponse extends User {
  access_token: string;
  token_type: string;
}

export interface UserListResponse {
  users: User[];
}

export interface UserDeleteResponse {
  message: string;
}
