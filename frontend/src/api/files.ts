import { apiClient } from './client';
import type { DocumentOut, DocumentStatusResponse, UploadResponse } from '../types';

interface UploadSingleFileArgs {
  file: File;
  projectId?: string;
  docType?: string;
  onProgress?: (progress: number) => void;
}

export async function listFiles(): Promise<DocumentOut[]> {
  const response = await apiClient.get<DocumentOut[]>('/api/files');
  return response.data;
}

export async function uploadSingleFile({
  file,
  projectId,
  docType = 'general',
  onProgress,
}: UploadSingleFileArgs): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('doc_type', docType);
  if (projectId) {
    formData.append('project_id', projectId);
  }

  const response = await apiClient.post<UploadResponse>('/api/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (event) => {
      if (!onProgress || !event.total) {
        return;
      }
      onProgress(Math.round((event.loaded / event.total) * 100));
    },
  });

  return response.data;
}

export async function getFileStatus(documentId: string): Promise<DocumentStatusResponse> {
  const response = await apiClient.get<DocumentStatusResponse>(`/api/files/${documentId}/status`);
  return response.data;
}
