import axios, { AxiosInstance, AxiosError } from 'axios';

// Types
export interface Client {
  id: string;
  name: string;
  slug: string;
  email: string;
  vertical: string;
  status: string;
  phone?: string;
  website?: string;
  timezone: string;
  ai_persona_name: string;
  services_offered?: string[];
  created_at: string;
}

export interface Lead {
  id: string;
  client_id: string;
  phone: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  status: string;
  score: string;
  score_value: number;
  source?: string;
  initial_channel: string;
  service_interested?: string;
  timeline?: string;
  budget_range?: string;
  qualified_at?: string;
  appointment_scheduled_at?: string;
  handed_off_at?: string;
  first_contact_at: string;
  last_contact_at: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  lead_id: string;
  channel: string;
  is_active: boolean;
  is_human_takeover: boolean;
  message_count: number;
  avg_confidence_score: number;
  started_at: string;
  last_message_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  confidence_score?: number;
  intent_detected?: string;
  created_at: string;
}

export interface KnowledgeBaseEntry {
  id: string;
  client_id: string;
  title: string;
  content: string;
  category?: string;
  source?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_leads: number;
  new_leads_today: number;
  hot_leads: number;
  warm_leads: number;
  appointments_today: number;
  appointments_this_week: number;
  avg_response_time_seconds?: number;
  conversion_rate?: number;
}

export interface Appointment {
  id: string;
  client_id: string;
  lead_id: string;
  scheduled_at: string;
  duration_minutes: number;
  service_type?: string;
  notes?: string;
  status: string;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  client_id: string;
  is_active: boolean;
  is_superuser: boolean;
  is_client_admin: boolean;
}

// API Client
class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || '',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth
    this.client.interceptors.request.use((config) => {
      const token = this.token || localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor for errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  // Auth
  async login(email: string, password: string): Promise<AuthToken> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await this.client.post<AuthToken>('/api/v1/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    this.setToken(response.data.access_token);
    return response.data;
  }

  async getMe(): Promise<User> {
    const response = await this.client.get<User>('/api/v1/auth/me');
    return response.data;
  }

  // Clients
  async getClients(): Promise<Client[]> {
    const response = await this.client.get<Client[]>('/api/v1/clients');
    return response.data;
  }

  async getClient(clientId: string): Promise<Client> {
    const response = await this.client.get<Client>(`/api/v1/clients/${clientId}`);
    return response.data;
  }

  async updateClient(clientId: string, data: Partial<Client>): Promise<Client> {
    const response = await this.client.patch<Client>(`/api/v1/clients/${clientId}`, data);
    return response.data;
  }

  // Leads
  async getLeads(clientId: string, params?: { status?: string; score?: string }): Promise<Lead[]> {
    const response = await this.client.get<Lead[]>(`/api/v1/clients/${clientId}/leads`, { params });
    return response.data;
  }

  async getLead(clientId: string, leadId: string): Promise<Lead> {
    const response = await this.client.get<Lead>(`/api/v1/clients/${clientId}/leads/${leadId}`);
    return response.data;
  }

  async getHotLeads(clientId: string, sinceHours: number = 24): Promise<Lead[]> {
    const response = await this.client.get<Lead[]>(
      `/api/v1/clients/${clientId}/leads/hot`,
      { params: { since_hours: sinceHours } }
    );
    return response.data;
  }

  async updateLead(clientId: string, leadId: string, data: Partial<Lead>): Promise<Lead> {
    const response = await this.client.patch<Lead>(`/api/v1/clients/${clientId}/leads/${leadId}`, data);
    return response.data;
  }

  // Conversations
  async getConversations(clientId: string, leadId: string): Promise<Conversation[]> {
    const response = await this.client.get<Conversation[]>(
      `/api/v1/clients/${clientId}/leads/${leadId}/conversations`
    );
    return response.data;
  }

  async getMessages(conversationId: string): Promise<Message[]> {
    const response = await this.client.get<Message[]>(`/api/v1/conversations/${conversationId}/messages`);
    return response.data;
  }

  // Knowledge Base
  async getKnowledgeBase(clientId: string, category?: string): Promise<KnowledgeBaseEntry[]> {
    const response = await this.client.get<KnowledgeBaseEntry[]>(
      `/api/v1/clients/${clientId}/knowledge`,
      { params: { category } }
    );
    return response.data;
  }

  async createKnowledgeEntry(
    clientId: string,
    data: { title: string; content: string; category?: string }
  ): Promise<KnowledgeBaseEntry> {
    const response = await this.client.post<KnowledgeBaseEntry>(
      `/api/v1/clients/${clientId}/knowledge`,
      data
    );
    return response.data;
  }

  async deleteKnowledgeEntry(clientId: string, entryId: string): Promise<void> {
    await this.client.delete(`/api/v1/clients/${clientId}/knowledge/${entryId}`);
  }

  // Dashboard
  async getDashboardStats(clientId: string): Promise<DashboardStats> {
    const response = await this.client.get<DashboardStats>(`/api/v1/clients/${clientId}/dashboard`);
    return response.data;
  }

  // Appointments
  async getAppointments(clientId: string, startDate?: string, endDate?: string): Promise<Appointment[]> {
    const response = await this.client.get<Appointment[]>(
      `/api/v1/clients/${clientId}/appointments`,
      { params: { start_date: startDate, end_date: endDate } }
    );
    return response.data;
  }

  async createAppointment(
    clientId: string,
    data: {
      lead_id: string;
      scheduled_at: string;
      duration_minutes?: number;
      service_type?: string;
      notes?: string;
    }
  ): Promise<Appointment> {
    const response = await this.client.post<Appointment>(
      `/api/v1/clients/${clientId}/appointments`,
      data
    );
    return response.data;
  }
}

export const api = new ApiClient();
