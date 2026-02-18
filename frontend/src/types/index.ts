// API Types for AI Lead System Dashboard

// =============================================================================
// Enums
// =============================================================================

export type ClientStatus = 'active' | 'paused' | 'onboarding' | 'churned';
export type LeadStatus = 
  | 'new' 
  | 'qualifying' 
  | 'qualified' 
  | 'appointment_booked' 
  | 'handed_off' 
  | 'nurturing' 
  | 'closed_won' 
  | 'closed_lost' 
  | 'disqualified';
export type LeadScore = 'hot' | 'warm' | 'cold' | 'unscored';
export type ChannelType = 'web_form' | 'sms' | 'whatsapp' | 'voice' | 'live_chat' | 'email' | 'missed_call';
export type MessageRole = 'lead' | 'agent' | 'human' | 'system';
export type EscalationReason = 
  | 'lead_request' 
  | 'low_confidence' 
  | 'high_value' 
  | 'long_conversation' 
  | 'negative_sentiment' 
  | 'agent_error';

// =============================================================================
// Core Models
// =============================================================================

export interface Client {
  id: string;
  name: string;
  slug: string;
  industry: string | null;
  status: ClientStatus;
  timezone: string;
  primary_language: string;
  notification_email: string | null;
  notification_phone: string | null;
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
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  status: LeadStatus;
  score: LeadScore;
  source: string | null;
  source_detail: string | null;
  service_interest: string | null;
  urgency: string | null;
  budget_range: string | null;
  location: string | null;
  preferred_contact_time: string | null;
  qualification_data: Record<string, unknown>;
  appointment_at: string | null;
  handed_off_at: string | null;
  crm_contact_id: string | null;
  crm_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  client_id: string;
  lead_id: string;
  channel: ChannelType;
  session_id: string | null;
  is_active: boolean;
  is_escalated: boolean;
  escalation_reason: EscalationReason | null;
  escalation_details: string | null;
  escalated_at: string | null;
  message_count: number;
  summary: string | null;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
  lead?: Lead;
  messages?: Message[];
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  tokens_input: number;
  tokens_output: number;
  model_used: string | null;
  confidence_score: number | null;
  intent: string | null;
  processing_time_ms: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface KnowledgeBase {
  id: string;
  client_id: string;
  name: string;
  description: string | null;
  document_count: number;
  is_active: boolean;
  created_at: string;
}

export interface Escalation {
  id: string;
  client_id: string;
  conversation_id: string;
  lead_id: string;
  reason: EscalationReason;
  reason_details: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  created_at: string;
}

// =============================================================================
// Dashboard Stats
// =============================================================================

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

export interface LeadsByStatus {
  status: LeadStatus;
  count: number;
}

// =============================================================================
// API Requests/Responses
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface CreateClientRequest {
  name: string;
  slug: string;
  industry?: string;
  timezone?: string;
  primary_language?: string;
  notification_email?: string;
  config?: Record<string, unknown>;
}

export interface UpdateClientRequest {
  name?: string;
  industry?: string;
  timezone?: string;
  primary_language?: string;
  notification_email?: string;
  notification_phone?: string;
}

export interface ClientConfigUpdate {
  business_name?: string;
  services?: string[];
  business_hours?: string;
  tone?: string;
  custom_instructions?: string;
  qualification_questions?: string[];
  hot_lead_triggers?: string[];
  escalation_triggers?: string[];
  response_delay_ms?: number;
  twilio_phone_number?: string;
  twilio_whatsapp_number?: string;
  hot_lead_sms_number?: string;
  calcom_api_key?: string;
  calcom_event_type_id?: number;
}

export interface LeadFilters {
  status?: LeadStatus;
  score?: LeadScore;
  channel?: ChannelType;
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface ConversationFilters {
  is_active?: boolean;
  is_escalated?: boolean;
  channel?: ChannelType;
  date_from?: string;
  date_to?: string;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
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
  knowledge_base: string;
  similarity: number;
}

// =============================================================================
// Auth
// =============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'client' | 'viewer';
  client_id?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}
