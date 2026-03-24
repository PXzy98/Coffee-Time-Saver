import { apiClient } from './client';
import type { RiskAnalyzerRunRequest, RiskReport, RunStatusResponse, ToolRegistryItem } from '../types';

export async function listTools(): Promise<ToolRegistryItem[]> {
  const response = await apiClient.get<ToolRegistryItem[]>('/api/tools/registry');
  return response.data;
}

export async function runRiskAnalysis(payload: RiskAnalyzerRunRequest): Promise<RunStatusResponse> {
  const response = await apiClient.post<RunStatusResponse>('/api/tools/risk-analyzer/run', payload);
  return response.data;
}

export async function getRiskStatus(reportId: string): Promise<RunStatusResponse> {
  const response = await apiClient.get<RunStatusResponse>(`/api/tools/risk-analyzer/status/${reportId}`);
  return response.data;
}

export async function getRiskReport(reportId: string): Promise<RiskReport> {
  const response = await apiClient.get<RiskReport>(`/api/tools/risk-analyzer/report/${reportId}`);
  return response.data;
}

export async function downloadRiskReport(reportId: string, format: 'pdf' | 'docx'): Promise<Blob> {
  const response = await apiClient.get(`/api/tools/risk-analyzer/report/${reportId}/download`, {
    params: { format },
    responseType: 'blob',
  });
  return response.data as Blob;
}
