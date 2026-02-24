export type ClientStatus = 'active' | 'paused' | 'onboarding' | 'churned';
export type LeadStatus = 'new' | 'qualifying' | 'qualified' | 'appointment_booked' | 'handed_off' | 'nurturing' | 'closed_won' | 'closed_lost' | 'disqualified';
export type LeadScore = 'hot' | 'warm' | 'cold' | 'unscored';
export type ChannelType = 'web_form' | 'sms' | 'whatsapp' | 'voice' | 'live_chat' | 'email' | 'missed_call';

export interface Client {
  id: string;
  name: string;
  slug: string;
  industry: string | null;
  status: ClientStatus;
  timezone: string;
  primary_language: string;
  config: Record<string, unknown>;
  tokens_used_this_month: number;
  monthly_token_budget: number;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  client_id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  status: LeadStatus;
  score: LeadScore;
  source: string | null;
  service_interest: string | null;
  budget_range: string | null;
  urgency: string | null;
  location: string | null;
  qualification_data: Record<string, unknown>;
  appointment_at: string | null;
  handed_off_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  content_type: string;
  tokens_input: number;
  tokens_output: number;
  model_used: string | null;
  confidence_score: number | null;
  processing_time_ms: number | null;
  external_message_id: string | null;
  intent: string | null;
  sentiment: string | null;
  msg_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  client_id: string;
  lead_id: string;
  channel: ChannelType;
  is_active: boolean;
  is_escalated: boolean;
  escalation_reason: string | null;
  escalated_at: string | null;
  message_count: number;
  sentiment_score: number | null;
  ended_at: string | null;
  end_reason: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface Escalation {
  id: string;
  client_id: string;
  conversation_id: string;
  lead_id: string;
  reason: string;
  reason_details: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  created_at: string;
  lead_name: string | null;
  lead_phone: string | null;
  lead_email: string | null;
  lead_score: string | null;
  conversation_channel: string | null;
  message_count: number | null;
}

export interface KnowledgeBase {
  id: string;
  client_id: string;
  name: string;
  description: string | null;
  category: string;
  source_type: string;
  source_url: string | null;
  is_active: boolean;
  chunk_count: number;
  document_count: number;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_leads: number;
  leads_today: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  appointments_booked: number;
  active_conversations: number;
  escalations_pending: number;
  avg_response_time_ms: number;
  qualification_rate: number;
  tokens_used: number;
  tokens_budget: number;
}

export interface LeadsByDay {
  date: string;
  total: number;
  hot: number;
  warm: number;
  cold: number;
}

export interface LeadsByChannel {
  channel: ChannelType;
  count: number;
  percentage: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// Request types
export interface CreateClientRequest {
  name: string;
  slug: string;
  industry?: string;
  timezone?: string;
  primary_language?: string;
  config?: Record<string, unknown>;
}

export interface UpdateClientRequest {
  name?: string;
  industry?: string;
  timezone?: string;
  primary_language?: string;
  status?: ClientStatus;
}

export interface ClientConfigUpdate {
  [key: string]: unknown;
}

export interface LeadFilters {
  status?: LeadStatus;
  score?: LeadScore;
  search?: string;
}

export interface ConversationFilters {
  is_active?: boolean;
  is_escalated?: boolean;
  channel?: ChannelType;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
  category?: string;
  source_type?: string;
}

export interface IngestDocumentRequest {
  content: string;
  source: string;
  metadata?: Record<string, unknown>;
}

export interface IngestFAQRequest {
  question: string;
  answer: string;
  category?: string;
}

export interface SearchKnowledgeRequest {
  query: string;
  kb_ids?: string[];
  max_results?: number;
  similarity_threshold?: number;
}

export interface SearchResult {
  id: string;
  content: string;
  source: string;
  metadata: Record<string, unknown>;
  chunk_index: number;
  knowledge_base: string;
  similarity: number;
}
