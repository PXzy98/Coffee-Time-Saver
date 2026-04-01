import { apiClient } from './client';
import type {
  EmailBotConfigOut,
  EmailBotConfigUpdate,
  LLMConfigCreate,
  LLMConfigOut,
  LLMConfigUpdate,
  UserAdminOut,
  UserRoleUpdate,
} from '../types';

export async function listLlmConfigs(): Promise<LLMConfigOut[]> {
  const response = await apiClient.get<LLMConfigOut[]>('/api/settings/llm');
  return response.data;
}

export async function getActiveLlmConfig(): Promise<LLMConfigOut | null> {
  const response = await apiClient.get<{ config: LLMConfigOut | null }>('/api/settings/llm/active');
  return response.data.config;
}

export async function createLlmConfig(payload: LLMConfigCreate): Promise<LLMConfigOut> {
  const response = await apiClient.post<LLMConfigOut>('/api/settings/llm', payload);
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

export async function testLlmConfigById(configId: number): Promise<{ status: string; response?: string; detail?: string }> {
  const response = await apiClient.post<{ status: string; response?: string; detail?: string }>(
    `/api/settings/llm/test?config_id=${configId}`,
    {},
  );
  return response.data;
}

export async function getEmailStatus(): Promise<{ configured: boolean; connected: boolean }> {
  const response = await apiClient.get<{ configured: boolean; connected: boolean }>('/api/settings/email-status');
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
