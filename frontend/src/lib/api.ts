/**
 * API client for the Data Analyst Copilot backend
 */

let API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

if (typeof window !== 'undefined' && API_BASE.includes('localhost')) {
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    API_BASE = API_BASE.replace('localhost', window.location.hostname);
  }
}

import { auth } from './firebase';

export interface ProcessResponse {
  message: string;
  dataset_id: string;
}

export interface DatasetStatus {
  status: 'processing' | 'ready' | 'error';
  error_message?: string;
  rows?: number;
  columns?: number;
  column_names?: string[];
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  missing: number;
  missing_pct: number;
  unique: number;
  unique_pct: number;
  sample_values: unknown[];
  stats: Record<string, unknown> | null;
}

export interface DatasetProfile {
  dataset_id: string;
  filename: string;
  rows: number;
  columns: number;
  total_missing: number;
  total_missing_pct: number;
  duplicates: number;
  memory_usage_mb: number;
  column_profiles: ColumnProfile[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
}

export interface EDAChart {
  chart_type: string;
  title: string;
  column?: string;
  image_url: string;
  insight?: string;
}

export interface EDAResponse {
  dataset_id: string;
  charts: EDAChart[];
  summary_insight?: string;
}

export interface ChatMessage {
  conversation_id: string;
  message_id: string;
  role: string;
  content: string;
  code?: string;
  chart_url?: string;
  table_data?: Record<string, unknown>;
  intent?: string;
  execution_time_ms?: number;
}

export interface SuggestedQuestion {
  question: string;
  category: string;
  icon: string;
}

export interface Dataset {
  id: string;
  filename: string;
  rows: number;
  columns: number;
  file_size: number;
  status?: string;
  created_at: string;
}

export interface StatResponse {
  analysis_type: string;
  result: Record<string, unknown>;
  chart_url?: string;
  interpretation?: string;
}

export interface SQLResponse {
  query: string;
  rows: number;
  columns: string[];
  data: Record<string, unknown>[];
  execution_time_ms: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const headers: Record<string, string> = {};
    if (auth.currentUser) {
      try {
        const token = await auth.currentUser.getIdToken();
        headers['Authorization'] = `Bearer ${token}`;
      } catch (e) {
        console.error("Failed to get auth token", e);
      }
    }
    return headers;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const authHeaders = await this.getAuthHeaders();
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  // ─── Upload ──────────────────────────────────────────────────────────────────

  async processDataset(
    datasetId: string,
    filename: string,
    filePath: string,
    fileSize: number
  ): Promise<ProcessResponse> {
    return this.request<ProcessResponse>('/api/upload/process', {
      method: 'POST',
      body: JSON.stringify({
        dataset_id: datasetId,
        filename,
        file_path: filePath,
        file_size: fileSize,
      }),
    });
  }

  async getDatasetStatus(datasetId: string): Promise<DatasetStatus> {
    return this.request<DatasetStatus>(`/api/upload/${datasetId}/status`);
  }

  async listDatasets(): Promise<Dataset[]> {
    return this.request<Dataset[]>('/api/upload/datasets');
  }

  async deleteDataset(datasetId: string): Promise<void> {
    await this.request(`/api/upload/${datasetId}`, { method: 'DELETE' });
  }

  // ─── Profile ─────────────────────────────────────────────────────────────────

  async getProfile(datasetId: string): Promise<DatasetProfile> {
    return this.request<DatasetProfile>(`/api/profile/${datasetId}`);
  }

  async getPreview(datasetId: string, rows = 50, page = 1) {
    return this.request(`/api/profile/${datasetId}/preview?rows=${rows}&page=${page}`);
  }

  async getSchema(datasetId: string) {
    return this.request(`/api/profile/${datasetId}/schema`);
  }

  // ─── EDA ─────────────────────────────────────────────────────────────────────

  async runEDA(datasetId: string, includeInsights = true, forceRefresh = false): Promise<EDAResponse> {
    return this.request<EDAResponse>(
      `/api/eda/${datasetId}?include_insights=${includeInsights}&force_refresh=${forceRefresh}`
    );
  }

  // ─── Chat ─────────────────────────────────────────────────────────────────────

  async chat(
    datasetId: string,
    message: string,
    conversationId?: string,
    model = 'openrouter'
  ): Promise<ChatMessage> {
    return this.request<ChatMessage>('/api/chat/', {
      method: 'POST',
      body: JSON.stringify({
        dataset_id: datasetId,
        message,
        conversation_id: conversationId,
        model,
      }),
    });
  }

  async getChatHistory(conversationId: string) {
    return this.request(`/api/chat/history/${conversationId}`);
  }

  async getLatestChatHistory(datasetId: string) {
    return this.request(`/api/chat/history/by_dataset/${datasetId}`);
  }

  async getConversations(datasetId: string) {
    return this.request(`/api/chat/conversations/${datasetId}`);
  }

  // ─── Statistics ──────────────────────────────────────────────────────────────

  async analyzeStatistics(
    datasetId: string,
    analysisType: string,
    columns?: string[],
    targetColumn?: string
  ): Promise<StatResponse> {
    return this.request<StatResponse>('/api/statistics/analyze', {
      method: 'POST',
      body: JSON.stringify({
        dataset_id: datasetId,
        analysis_type: analysisType,
        columns,
        target_column: targetColumn,
      }),
    });
  }

  // ─── Cleaning ────────────────────────────────────────────────────────────────

  async cleanData(
    datasetId: string,
    operation: string,
    params: Record<string, unknown> = {}
  ) {
    return this.request('/api/cleaning/', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, operation, params }),
    });
  }

  async getCleaningSuggestions(datasetId: string, forceRefresh = false) {
    return this.request(`/api/cleaning/suggestions/${datasetId}?force_refresh=${forceRefresh}`);
  }

  // ─── SQL ─────────────────────────────────────────────────────────────────────

  async runSQL(datasetId: string, query: string): Promise<SQLResponse> {
    return this.request<SQLResponse>('/api/sql/query', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, query }),
    });
  }

  async nlToSQL(datasetId: string, question: string, model = 'openrouter') {
    return this.request(
      `/api/sql/nl-to-sql?dataset_id=${datasetId}&question=${encodeURIComponent(question)}&model=${model}`,
      { method: 'POST' }
    );
  }

  async getSQLSchema(datasetId: string) {
    return this.request(`/api/sql/schema/${datasetId}`);
  }

  // ─── Suggestions ─────────────────────────────────────────────────────────────

  async getSuggestions(datasetId: string, model = 'openrouter', forceRefresh = false): Promise<{ questions: SuggestedQuestion[] }> {
    return this.request(`/api/suggestions/${datasetId}?model=${model}&force_refresh=${forceRefresh}`);
  }

  // ─── Export ──────────────────────────────────────────────────────────────────

  async exportDataset(
    datasetId: string,
    format: 'csv' | 'excel' | 'pdf' | 'json',
    includeProfile = true
  ): Promise<void> {
    const authHeaders = await this.getAuthHeaders();
    
    const response = await fetch(`${this.baseUrl}/api/export/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify({
        dataset_id: datasetId,
        format,
        include_profile: includeProfile,
      }),
    });

    if (!response.ok) throw new Error('Export failed');

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const contentDisposition = response.headers.get('content-disposition') || '';
    const fileName = contentDisposition.split('filename=')[1]?.replace(/"/g, '') || `export.${format}`;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ─── Account & Privacy ───────────────────────────────────────────────────────

  async deleteUserDatasets(): Promise<void> {
    await this.request('/api/users/me/datasets', { method: 'DELETE' });
  }

  async deleteUserAccount(): Promise<void> {
    await this.request('/api/users/me', { method: 'DELETE' });
  }

  // ─── Health ───────────────────────────────────────────────────────────────────

  async healthCheck(): Promise<{ status: string }> {
    return this.request('/api/health');
  }
}

export const api = new ApiClient(API_BASE);
export default api;
