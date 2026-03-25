export type Locale = 'en' | 'fr';

export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  preferred_lang: Locale;
  roles: string[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export interface MetricsOut {
  active_projects: number;
  overdue_tasks: number;
  pending_tasks: number;
  files_processed_today: number;
  unread_emails: number;
}

export interface ActivityItem {
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
}

export interface DashboardOut {
  metrics: MetricsOut;
  recent_activity: ActivityItem[];
}

export interface BriefingOut {
  id: string;
  date: string;
  content_en: string | null;
  content_fr: string | null;
  generated_at: string;
}

export interface TaskOut {
  id: string;
  title: string;
  description: string | null;
  priority: number;
  due_date: string | null;
  is_completed: boolean;
  completed_at: string | null;
  source: string;
  sort_score: number | null;
  project_id: string | null;
  created_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  priority?: number;
  due_date?: string | null;
  project_id?: string | null;
  source?: string;
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  priority?: number;
  due_date?: string | null;
  is_completed?: boolean;
  project_id?: string | null;
}

export interface ProjectMember {
  user_id: string;
  role: string;
}

export interface ProjectOut {
  id: string;
  name: string;
  description: string | null;
  status: string;
  owner_id: string | null;
  is_shared: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  members: ProjectMember[];
}

export interface ProjectCreate {
  name: string;
  description?: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

export interface ProjectUpdate {
  name?: string;
  description?: string | null;
  status?: string;
  metadata?: Record<string, unknown>;
}

export interface DocumentOut {
  id: string;
  filename: string;
  mime_type: string | null;
  file_size_bytes: number | null;
  status: string;
  source: string;
  doc_type: string;
  project_id: string | null;
  created_at: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface DocumentStatusResponse {
  document_id: string;
  status: string;
}

export interface ToolRegistryItem {
  slug: string;
  name_en: string;
  name_fr: string;
  description_en: string | null;
  description_fr: string | null;
  icon: string | null;
  api_endpoint: string;
}

export interface LLMConfigOut {
  id: number;
  name: string;
  provider: string;
  api_url: string;
  model: string;
  is_active: boolean;
}

export interface LLMConfigUpdate {
  provider?: string;
  api_url?: string;
  api_key?: string;
  model?: string;
  is_active?: boolean;
}

export interface EmailBotConfigOut {
  imap_host: string;
  imap_port: number;
  imap_user: string;
  imap_folder: string;
  poll_interval_seconds: number;
}

export interface EmailBotConfigUpdate {
  imap_host?: string;
  imap_port?: number;
  imap_user?: string;
  imap_password?: string;
  imap_folder?: string;
  poll_interval_seconds?: number;
}

export interface UserAdminOut {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: string[];
}

export interface UserRoleUpdate {
  roles: string[];
}

export interface RiskAnalyzerRunRequest {
  project_id: string;
  include_web_search: boolean;
}

export interface RiskItem {
  id: string;
  description: string;
  category: string;
  likelihood: number;
  impact: number;
  risk_score: number;
  confidence: number;
  source_documents: string[];
  source_quotes: string[];
  mitigation: string;
}

export interface InconsistencyItem {
  id: string;
  type: string;
  document_a: string;
  passage_a: string;
  document_b: string;
  passage_b: string;
  explanation: string;
  confidence: number;
  recommendation: string;
}

export interface RiskReport {
  report_id: string;
  project_id: string;
  generated_at: string;
  overall_risk_level: string;
  overall_confidence: number;
  executive_summary: string;
  risks: RiskItem[];
  inconsistencies: InconsistencyItem[];
  documents_analyzed: string[];
  methodology_notes: string;
}

export interface RunStatusResponse {
  report_id: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | string;
  message?: string | null;
}

export interface WsEvent<T = unknown> {
  type: string;
  payload: T;
}

export interface ProjectSuggestionPayload {
  document_id: string;
  document_name: string;
  match_type: 'existing' | 'new';
  project_id: string | null;
  project_name: string;
  confidence: number;
  reason: string;
}
