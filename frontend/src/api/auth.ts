import { apiClient, rawClient } from './client';
import type { LoginRequest, TokenResponse, UserResponse } from '../types';

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const response = await rawClient.post<TokenResponse>('/api/auth/login', payload);
  return response.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>('/api/auth/me');
  return response.data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout');
}
