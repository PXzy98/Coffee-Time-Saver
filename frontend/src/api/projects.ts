import { apiClient } from './client';
import type { ProjectCreate, ProjectOut, ProjectUpdate } from '../types';

export async function listProjects(): Promise<ProjectOut[]> {
  const response = await apiClient.get<ProjectOut[]>('/api/projects');
  return response.data;
}

export async function getProject(projectId: string): Promise<ProjectOut> {
  const response = await apiClient.get<ProjectOut>(`/api/projects/${projectId}`);
  return response.data;
}

export async function createProject(payload: ProjectCreate): Promise<ProjectOut> {
  const response = await apiClient.post<ProjectOut>('/api/projects', payload);
  return response.data;
}

export async function updateProject(projectId: string, payload: ProjectUpdate): Promise<ProjectOut> {
  const response = await apiClient.patch<ProjectOut>(`/api/projects/${projectId}`, payload);
  return response.data;
}

export async function toggleProjectShare(projectId: string, isShared: boolean): Promise<ProjectOut> {
  const response = await apiClient.patch<ProjectOut>(`/api/projects/${projectId}/share`, null, {
    params: { is_shared: isShared },
  });
  return response.data;
}
