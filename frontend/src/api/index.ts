// API Client for AI Lead System Dashboard

import axios, { AxiosInstance, AxiosError } from 'axios';
import toast from 'react-hot-toast';
import type {
  Client,
  Lead,
  Conversation,
  Message,
  KnowledgeBase,
  DashboardStats,
  LeadsByDay,
  LeadsByChannel,
  PaginatedResponse,
  CreateClientRequest,
  UpdateClientRequest,
  ClientConfigUpdate,
  LeadFilters,
  ConversationFilters,
  CreateKnowledgeBaseRequest,
  IngestDocumentRequest,
  IngestFAQRequest,
  SearchKnowledgeRequest,
  SearchResult,
  Escalation,
} from '../types';

// =============================================================================
// API Client Setup
// =============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  const apiKey = localStorage.getItem('api_key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const message = (error.response?.data as { detail?: string })?.detail || error.message;
    
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    } else if (error.response?.status === 403) {
      toast.error('Access denied');
    } else if (error.response?.status === 404) {
      toast.error('Resource not found');
    } else if (error.response?.status === 422) {
      toast.error('Invalid request data');
    } else if (error.response?.status && error.response.status >= 500) {
      toast.error('Server error. Please try again.');
    } else {
      toast.error(message);
    }
    
    return Promise.reject(error);
  }
);

// =============================================================================
// Dashboard / Stats
// =============================================================================

export const dashboardApi = {
  getStats: async (clientId: string): Promise<DashboardStats> => {
    const { data } = await api.get(`/api/v1/dashboard/${clientId}/stats`);
    return data;
  },

  getLeadsByDay: async (clientId: string, days = 30): Promise<LeadsByDay[]> => {
    const { data } = await api.get(`/api/v1/dashboard/${clientId}/leads-by-day`, {
      params: { days },
    });
    return data;
  },

  getLeadsByChannel: async (clientId: string): Promise<LeadsByChannel[]> => {
    const { data } = await api.get(`/api/v1/dashboard/${clientId}/leads-by-channel`);
    return data;
  },

  getRecentActivity: async (clientId: string, limit = 10): Promise<Lead[]> => {
    const { data } = await api.get(`/api/v1/leads/client/${clientId}`, {
      params: { limit, sort: 'created_at:desc' },
    });
    return data.items || data;
  },
};

// =============================================================================
// Clients
// =============================================================================

export const clientsApi = {
  list: async (): Promise<Client[]> => {
    const { data } = await api.get('/api/v1/clients');
    return data;
  },

  get: async (id: string): Promise<Client> => {
    const { data } = await api.get(`/api/v1/clients/${id}`);
    return data;
  },

  getBySlug: async (slug: string): Promise<Client> => {
    const { data } = await api.get(`/api/v1/clients/slug/${slug}`);
    return data;
  },

  create: async (request: CreateClientRequest): Promise<Client & { api_key: string }> => {
    const { data } = await api.post('/api/v1/clients', request);
    return data;
  },

  update: async (id: string, request: UpdateClientRequest): Promise<Client> => {
    const { data } = await api.patch(`/api/v1/clients/${id}`, request);
    return data;
  },

  updateConfig: async (id: string, config: ClientConfigUpdate): Promise<Client> => {
    const { data } = await api.patch(`/api/v1/clients/${id}/config`, config);
    return data;
  },

  getConfig: async (id: string): Promise<Record<string, unknown>> => {
    const { data } = await api.get(`/api/v1/clients/${id}/config`);
    return data;
  },

  activate: async (id: string): Promise<Client> => {
    const { data } = await api.post(`/api/v1/clients/${id}/activate`);
    return data;
  },

  pause: async (id: string): Promise<Client> => {
    const { data } = await api.post(`/api/v1/clients/${id}/pause`);
    return data;
  },

  rotateApiKey: async (id: string): Promise<{ api_key: string }> => {
    const { data } = await api.post(`/api/v1/clients/${id}/rotate-api-key`);
    return data;
  },

  getUsage: async (id: string): Promise<{ tokens_used: number; budget: number; percent: number }> => {
    const { data } = await api.get(`/api/v1/clients/${id}/usage`);
    return data;
  },
};

// =============================================================================
// Leads
// =============================================================================

export const leadsApi = {
  list: async (
    clientId: string,
    filters?: LeadFilters,
    page = 1,
    perPage = 20
  ): Promise<PaginatedResponse<Lead>> => {
    const { data } = await api.get(`/api/v1/leads/client/${clientId}`, {
      params: { ...filters, page, per_page: perPage },
    });
    return data;
  },

  get: async (id: string): Promise<Lead> => {
    const { data } = await api.get(`/api/v1/leads/${id}`);
    return data;
  },

  update: async (id: string, updates: Partial<Lead>): Promise<Lead> => {
    const { data } = await api.patch(`/api/v1/leads/${id}`, updates);
    return data;
  },

  updateScore: async (id: string, score: string): Promise<Lead> => {
    const { data } = await api.patch(`/api/v1/leads/${id}/score`, { score });
    return data;
  },

  updateStatus: async (id: string, status: string): Promise<Lead> => {
    const { data } = await api.patch(`/api/v1/leads/${id}/status`, { status });
    return data;
  },

  handoff: async (id: string, notes?: string): Promise<Lead> => {
    const { data } = await api.post(`/api/v1/leads/${id}/handoff`, { notes });
    return data;
  },

  getHotLeads: async (clientId: string): Promise<Lead[]> => {
    const { data } = await api.get(`/api/v1/leads/client/${clientId}/hot`);
    return data;
  },

  scheduleAppointment: async (
    id: string,
    appointmentTime: string,
    notes?: string
  ): Promise<Lead> => {
    const { data } = await api.post(`/api/v1/leads/${id}/appointment`, {
      appointment_time: appointmentTime,
      notes,
    });
    return data;
  },
};

// =============================================================================
// Conversations
// =============================================================================

export const conversationsApi = {
  list: async (
    clientId: string,
    filters?: ConversationFilters,
    page = 1,
    perPage = 20
  ): Promise<PaginatedResponse<Conversation>> => {
    const { data } = await api.get(`/api/v1/conversations/client/${clientId}`, {
      params: { ...filters, page, per_page: perPage },
    });
    return data;
  },

  get: async (id: string): Promise<Conversation> => {
    const { data } = await api.get(`/api/v1/conversations/${id}`);
    return data;
  },

  getMessages: async (id: string, limit = 50): Promise<Message[]> => {
    const { data } = await api.get(`/api/v1/conversations/${id}/messages`, {
      params: { limit },
    });
    return data;
  },

  addMessage: async (id: string, content: string): Promise<Message> => {
    const { data } = await api.post(`/api/v1/conversations/${id}/messages`, {
      content,
      role: 'human',
    });
    return data;
  },

  escalate: async (id: string, reason: string, details?: string): Promise<Conversation> => {
    const { data } = await api.post(`/api/v1/conversations/${id}/escalate`, {
      reason,
      details,
    });
    return data;
  },

  end: async (id: string): Promise<Conversation> => {
    const { data } = await api.post(`/api/v1/conversations/${id}/end`);
    return data;
  },

  getActive: async (clientId: string): Promise<Conversation[]> => {
    const { data } = await api.get(`/api/v1/conversations/client/${clientId}/active`);
    return data;
  },

  getEscalated: async (clientId: string): Promise<Conversation[]> => {
    const { data } = await api.get(`/api/v1/conversations/client/${clientId}/escalated`);
    return data;
  },

  getMetrics: async (id: string): Promise<{ avg_response_time_ms: number; message_count: number }> => {
    const { data } = await api.get(`/api/v1/conversations/${id}/metrics`);
    return data;
  },
};

// =============================================================================
// Escalations
// =============================================================================

export const escalationsApi = {
  list: async (clientId: string, resolved = false): Promise<Escalation[]> => {
    const { data } = await api.get(`/api/v1/escalations/client/${clientId}`, {
      params: { resolved },
    });
    return data;
  },

  resolve: async (id: string, resolvedBy: string): Promise<Escalation> => {
    const { data } = await api.post(`/api/v1/escalations/${id}/resolve`, {
      resolved_by: resolvedBy,
    });
    return data;
  },
};

// =============================================================================
// Knowledge Base
// =============================================================================

export const knowledgeApi = {
  listBases: async (clientId: string): Promise<KnowledgeBase[]> => {
    const { data } = await api.get(`/api/v1/knowledge/client/${clientId}/bases`);
    return data;
  },

  getBase: async (id: string): Promise<KnowledgeBase> => {
    const { data } = await api.get(`/api/v1/knowledge/bases/${id}`);
    return data;
  },

  createBase: async (clientId: string, request: CreateKnowledgeBaseRequest): Promise<KnowledgeBase> => {
    const { data } = await api.post(`/api/v1/knowledge/bases`, request, {
      params: { client_id: clientId },
    });
    return data;
  },

  deleteBase: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/knowledge/bases/${id}`);
  },

  ingestDocument: async (kbId: string, request: IngestDocumentRequest): Promise<{ chunks_created: number }> => {
    const { data } = await api.post(`/api/v1/knowledge/bases/${kbId}/documents`, request);
    return data;
  },

  ingestFAQ: async (kbId: string, request: IngestFAQRequest): Promise<{ chunks_created: number }> => {
    const { data } = await api.post(`/api/v1/knowledge/bases/${kbId}/faqs`, request);
    return data;
  },

  bulkIngestFAQs: async (
    kbId: string,
    faqs: IngestFAQRequest[]
  ): Promise<{ faqs_processed: number; total_chunks_created: number }> => {
    const { data } = await api.post(`/api/v1/knowledge/bases/${kbId}/faqs/bulk`, { faqs });
    return data;
  },

  search: async (clientId: string, request: SearchKnowledgeRequest): Promise<SearchResult[]> => {
    const { data } = await api.post(`/api/v1/knowledge/search`, request, {
      params: { client_id: clientId },
    });
    return data.results;
  },

  getStats: async (kbId: string): Promise<{ chunk_count: number; document_count: number }> => {
    const { data } = await api.get(`/api/v1/knowledge/bases/${kbId}/stats`);
    return data;
  },

  clear: async (kbId: string): Promise<{ chunks_deleted: number }> => {
    const { data } = await api.post(`/api/v1/knowledge/bases/${kbId}/clear`);
    return data;
  },
};

// =============================================================================
// Health
// =============================================================================

export const healthApi = {
  check: async (): Promise<{ status: string; database: string }> => {
    const { data } = await api.get('/health/ready');
    return data;
  },
};

export default api;
