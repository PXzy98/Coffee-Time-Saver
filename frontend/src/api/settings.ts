import { apiClient } from './client';
import type {
  EmailBotConfigOut,
  EmailBotConfigUpdate,
  LLMConfigOut,
  LLMConfigUpdate,
  UserAdminOut,
  UserRoleUpdate,
} from '../types';

export async function listLlmConfigs(): Promise<LLMConfigOut[]> {
  const response = await apiClient.get<LLMConfigOut[]>('/api/settings/llm');
  return response.data;
}

export async function updateLlmConfig(configId: number, payload: LLMConfigUpdate): Promise<LLMConfigOut> {
  const response = await apiClient.put<LLMConfigOut>(`/api/settings/llm/${configId}`, payload);
  return response.data;
}

export async function testLlmConfig(payload: LLMConfigUpdate): Promise<{ status: string; response?: string; detail?: string }> {
  const response = await apiClient.post<{ status: string; response?: string; detail?: string }>(
    '/api/settings/llm/test',
    payload,
  );
  return response.data;
}

export async function getEmailConfig(): Promise<EmailBotConfigOut> {
  const response = await apiClient.get<EmailBotConfigOut>('/api/settings/email');
  return response.data;
}

export async function updateEmailConfig(payload: EmailBotConfigUpdate): Promise<{ detail: string }> {
  const response = await apiClient.put<{ detail: string }>('/api/settings/email', payload);
  return response.data;
}

export async function listUsers(): Promise<UserAdminOut[]> {
  const response = await apiClient.get<UserAdminOut[]>('/api/settings/users');
  return response.data;
}

export async function updateUserRoles(userId: string, payload: UserRoleUpdate): Promise<UserAdminOut> {
  const response = await apiClient.patch<UserAdminOut>(`/api/settings/users/${userId}`, payload);
  return response.data;
}
