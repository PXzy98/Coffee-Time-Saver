import { apiClient } from './client';
import type { TaskCreate, TaskOut, TaskUpdate } from '../types';

export async function listTasks(): Promise<TaskOut[]> {
  const response = await apiClient.get<TaskOut[]>('/api/tasks');
  return response.data;
}

export async function createTask(payload: TaskCreate): Promise<TaskOut[]> {
  const response = await apiClient.post<TaskOut[]>('/api/tasks', payload);
  return response.data;
}

export async function updateTask(taskId: string, payload: TaskUpdate): Promise<TaskOut[]> {
  const response = await apiClient.patch<TaskOut[]>(`/api/tasks/${taskId}`, payload);
  return response.data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/api/tasks/${taskId}`);
}
