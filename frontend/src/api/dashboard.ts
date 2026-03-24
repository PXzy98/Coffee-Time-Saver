import { apiClient } from './client';
import type { BriefingOut, DashboardOut } from '../types';

export async function getDashboard(): Promise<DashboardOut> {
  const response = await apiClient.get<DashboardOut>('/api/dashboard');
  return response.data;
}

export async function getTodayBriefing(): Promise<BriefingOut> {
  const response = await apiClient.get<BriefingOut>('/api/briefing/today');
  return response.data;
}
