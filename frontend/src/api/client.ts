import type {
  User, Patient, ReportUploadResponse, ReportAnalysisResponse,
  ReportSummary, HistoryPoint, MLPredictResponse, ParameterCorrection,
} from '../types/api';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const TOKEN_KEY = 'aegis_token';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean; isForm?: boolean } = {}
): Promise<T> {
  const { method = 'GET', body, auth = true, isForm = false } = options;
  const headers: Record<string, string> = {};
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: isForm ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      `Can't reach the AEGIS AI server at ${API_URL}. Check it's running and VITE_API_URL is correct.`,
      0
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === 'string') detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: { msg?: string }) => d.msg).join('; ');
    } catch {
      // response wasn't JSON -- keep the generic message
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  register: (email: string, password: string, fullName?: string) =>
    request<User>('/auth/register', { method: 'POST', body: { email, password, full_name: fullName }, auth: false }),

  login: async (email: string, password: string) => {
    const result = await request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    });
    setToken(result.access_token);
    return result;
  },

  logout: () => setToken(null),

  getMyProfile: () => request<Patient>('/patients/me'),
  updateMyProfile: (payload: Partial<Patient>) =>
    request<Patient>('/patients/me', { method: 'PUT', body: payload }),
  getMyHistory: () => request<HistoryPoint[]>('/patients/me/history'),

  uploadReport: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<ReportUploadResponse>('/reports/upload', { method: 'POST', body: form, isForm: true });
  },
  analyzeReport: (reportId: number, corrections?: ParameterCorrection[]) =>
    request<ReportAnalysisResponse>(`/reports/${reportId}/analyze`, {
      method: 'POST',
      body: { corrections },
    }),
  listReports: () => request<ReportSummary[]>('/reports'),
  getReport: (reportId: number) => request<ReportAnalysisResponse>(`/reports/${reportId}`),

  mlPredict: (payload: Record<string, unknown>) =>
    request<MLPredictResponse>('/ml/predict', { method: 'POST', body: payload, auth: false }),

  healthStatus: () => request<{ status: string }>('/health/status', { auth: false }),
};
