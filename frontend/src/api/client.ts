import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bi_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Automatic dual fallback: if direct 127.0.0.1:8000 fails, try /api proxy; if /api 404s, try direct 127.0.0.1:8000
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    if (config && !config._retried) {
      config._retried = true;
      if (config.baseURL === 'http://127.0.0.1:8000/api') {
        config.baseURL = '/api';
        return axios(config);
      }
      if (config.baseURL === '/api' || !config.baseURL) {
        config.baseURL = 'http://127.0.0.1:8000/api';
        return axios(config);
      }
    }
    return Promise.reject(error);
  }
);

export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface RemediationLog {
  id: number;
  column_name: string;
  issue_type: string;
  issue_description: string;
  resolution_strategy: string;
  resolution_details: string;
  created_at: string;
}

export interface DatasetFact {
  id: number;
  fact_type: string;
  title: string;
  description: string;
  metric_value?: string;
  created_at: string;
}

export interface ColumnMeta {
  name: string;
  type: string;
  original_type: string;
  null_count: number;
  unique_count: number;
}

export interface DatasetSummary {
  id: number;
  name: string;
  original_filename: string;
  physical_table_name: string;
  row_count: number;
  column_count: number;
  health_score: number;
  created_at: string;
}

export interface DatasetDetail extends DatasetSummary {
  columns_meta: ColumnMeta[];
  remediation_logs: RemediationLog[];
  facts: DatasetFact[];
  sample_data: Record<string, any>[];
}

export interface NumericSummary {
  column: string;
  min_val: number;
  max_val: number;
  avg_val: number;
  sum_val: number;
}

export interface KPICards {
  total_rows: number;
  total_cols: number;
  health_score: number;
  date_min?: string;
  date_max?: string;
  numeric_summaries: NumericSummary[];
}

export interface ChartData {
  id: string;
  title: string;
  chart_type: string;
  x_key: string;
  y_key: string;
  data: Record<string, any>[];
}

export interface DashboardResponse {
  kpis: KPICards;
  charts: ChartData[];
}

export interface SQLGenerateResponse {
  id: number;
  dataset_id: number;
  prompt: string;
  generated_sql: string;
  explanation: string;
  created_at: string;
}

export interface ChartSuggestion {
  chart_type: 'bar' | 'line' | 'scatter' | 'none';
  x_key: string | null;
  y_key: string | null;
  title: string;
  data?: Record<string, any>[];
  reason?: string;
}

export interface SQLExecuteResponse {
  columns: string[];
  rows: Record<string, any>[];
  total_rows: number;
  row_count?: number;
  execution_time_ms: number;
  chart_suggestion: ChartSuggestion;
}

export interface ChatMessage {
  id: number;
  dataset_id: number;
  user_id: number;
  role: 'user' | 'assistant';
  content: string;
  generated_sql?: string | null;
  explanation?: string | null;
  created_at: string;
}

export interface ChatPromptRequest {
  dataset_id: number;
  prompt: string;
  additional_dataset_ids?: number[];
}

export interface DatasetRelationship {
  source_dataset_id: number;
  source_dataset_name: string;
  source_column: string;
  target_dataset_id: number;
  target_dataset_name: string;
  target_column: string;
  overlap_count: number;
  join_type: string;
  sample_overlap_values: any[];
}

export interface NLChartGenerateRequest {
  dataset_id: number;
  prompt: string;
  chart_type?: string;
  api_key?: string;
}

export interface NLChartGenerateResponse {
  title: string;
  chart_type: 'bar' | 'line' | 'scatter' | 'pie' | 'area';
  x_key: string;
  y_key: string;
  data: Record<string, any>[];
  explanation: string;
  generated_sql: string;
  total_data_points: number;
}

export const generateNLChart = async (data: NLChartGenerateRequest): Promise<NLChartGenerateResponse> => {
  const res = await api.post<NLChartGenerateResponse>('/sql-studio/generate-chart', data);
  return res.data;
};

export const executeSQL = async (dataset_id: number, sql: string): Promise<SQLExecuteResponse> => {
  const res = await api.post<SQLExecuteResponse>('/sql-studio/execute', { dataset_id, sql });
  return res.data;
};

export const sendChatMessage = async (data: ChatPromptRequest): Promise<ChatMessage> => {
  const res = await api.post<ChatMessage>('/sql-studio/chat', data);
  return res.data;
};

export const getChatHistory = async (dataset_id: number): Promise<ChatMessage[]> => {
  const res = await api.get<ChatMessage[]>(`/sql-studio/chat/${dataset_id}`);
  return res.data;
};

export const clearChatHistory = async (dataset_id: number): Promise<{ message: string }> => {
  const res = await api.delete<{ message: string }>(`/sql-studio/chat/${dataset_id}`);
  return res.data;
};

export const getDatasetRelationships = async (): Promise<DatasetRelationship[]> => {
  const res = await api.get<DatasetRelationship[]>('/datasets/relationships');
  return res.data;
};

export const downloadExecutivePDF = async (dataset_id: number, dataset_name: string): Promise<void> => {
  const res = await api.get(`/datasets/${dataset_id}/report/pdf`, {
    responseType: 'blob'
  });
  const blob = new Blob([res.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `${dataset_name.replace(/\s+/g, '_')}_Executive_Dossier.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export interface PrivacyAuditResponse {
  dataset_id: number;
  dataset_name: string;
  physical_table_name: string;
  real_rows_count: number;
  synthetic_rows_count: number;
  epsilon: number;
  delta: number;
  pii_columns_scrubbed: string[];
  topological_fidelity_score: number;
  privacy_guarantee: string;
  surrogate_preview: Record<string, any>[];
  surrogate_columns: string[];
}

export const getPrivacyAudit = async (dataset_id: number, epsilon: number = 1.0): Promise<PrivacyAuditResponse> => {
  const res = await api.get<PrivacyAuditResponse>(`/datasets/${dataset_id}/privacy-audit?epsilon=${epsilon}`);
  return res.data;
};
