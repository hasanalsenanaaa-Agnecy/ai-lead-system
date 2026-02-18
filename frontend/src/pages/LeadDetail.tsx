import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  PhoneIcon,
  EnvelopeIcon,
  CalendarIcon,
  ChatBubbleLeftRightIcon,
  UserIcon,
  ClockIcon,
  MapPinIcon,
  CurrencyDollarIcon,
  BriefcaseIcon,
  FireIcon,
  SunIcon,
  CloudIcon,
  PaperAirplaneIcon,
  HandRaisedIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { apiClient, Lead, Conversation, Message } from '../utils/api';
import toast from 'react-hot-toast';

function LeadScoreBadge({ score }: { score: string }) {
  const config = {
    hot: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: FireIcon },
    warm: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: SunIcon },
    cold: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200', icon: CloudIcon },
  };
  const { bg, text, border, icon: Icon } = config[score as keyof typeof config] || config.cold;

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${bg} ${text} border ${border}`}>
      <Icon className="w-4 h-4 mr-1.5" />
      {score.toUpperCase()}
    </span>
  );
}

function InfoItem({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | null | undefined;
}) {
  if (!value) return null;
  return (
    <div className="flex items-start space-x-3 py-2">
      <Icon className="h-5 w-5 text-gray-400 mt-0.5" />
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-sm text-gray-900">{value}</p>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isLead = message.role === 'lead';
  const isAI = message.role === 'ai';
  const isHuman = message.role === 'human';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <span className="px-3 py-1 bg-gray-100 text-gray-500 text-xs rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex ${isLead ? 'justify-start' : 'justify-end'} mb-4`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isLead
            ? 'bg-gray-100 text-gray-900 rounded-tl-none'
            : isAI
            ? 'bg-primary-600 text-white rounded-tr-none'
            : 'bg-green-600 text-white rounded-tr-none'
        }`}
      >
        <div className="flex items-center space-x-2 mb-1">
          <span className="text-xs opacity-70">
            {isLead ? 'Lead' : isAI ? '🤖 AI Assistant' : '👤 Human Agent'}
          </span>
          {message.confidence_score && !isLead && (
            <span className="text-xs opacity-60">
              • {Math.round(message.confidence_score * 100)}% confidence
            </span>
          )}
        </div>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <p className={`text-xs mt-2 ${isLead ? 'text-gray-500' : 'opacity-70'}`}>
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  );
}

function ConversationPanel({
  conversation,
  clientId,
}: {
  conversation: Conversation;
  clientId: string;
}) {
  const [newMessage, setNewMessage] = useState('');
  const queryClient = useQueryClient();

  const { data: messages, isLoading } = useQuery({
    queryKey: ['messages', conversation.id],
    queryFn: () => apiClient.getMessages(conversation.id),
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      // This would call an API endpoint to send a manual message
      // For now, we'll just show a toast
      return content;
    },
    onSuccess: () => {
      setNewMessage('');
      queryClient.invalidateQueries({ queryKey: ['messages', conversation.id] });
      toast.success('Message sent');
    },
  });

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (newMessage.trim()) {
      sendMessageMutation.mutate(newMessage);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Conversation Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-3">
          <ChatBubbleLeftRightIcon className="h-5 w-5 text-gray-500" />
          <div>
            <p className="text-sm font-medium text-gray-900">
              {conversation.channel === 'whatsapp' ? 'WhatsApp' : 'SMS'} Conversation
            </p>
            <p className="text-xs text-gray-500">
              Started {new Date(conversation.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        {conversation.human_takeover && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
            <HandRaisedIcon className="w-3 h-3 mr-1" />
            Human Takeover
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : messages && messages.length > 0 ? (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>No messages yet</p>
          </div>
        )}
      </div>

      {/* Message Input */}
      <form onSubmit={handleSendMessage} className="border-t border-gray-200 p-4">
        <div className="flex items-center space-x-3">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type a message to take over the conversation..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          <button
            type="submit"
            disabled={!newMessage.trim() || sendMessageMutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PaperAirplaneIcon className="h-5 w-5" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Sending a message will trigger human takeover for this conversation
        </p>
      </form>
    </div>
  );
}

export default function LeadDetail() {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const clientId = localStorage.getItem('clientId') || '';

  const { data: leads } = useQuery({
    queryKey: ['leads', clientId],
    queryFn: () => apiClient.getLeads(clientId),
    enabled: !!clientId,
  });

  const lead = leads?.find((l) => l.id === leadId);

  const { data: conversations, isLoading: conversationsLoading } = useQuery({
    queryKey: ['conversations', clientId, leadId],
    queryFn: () => apiClient.getConversations(clientId, leadId!),
    enabled: !!clientId && !!leadId,
  });

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const activeConversation = conversations?.find((c) => c.id === activeConversationId) || conversations?.[0];

  const updateLeadMutation = useMutation({
    mutationFn: async (updates: Partial<Lead>) => {
      return apiClient.updateLead(leadId!, updates);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead updated');
    },
    onError: () => {
      toast.error('Failed to update lead');
    },
  });

  if (!lead) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-gray-300 mx-auto" />
          <p className="mt-2 text-gray-500">Lead not found</p>
          <Link to="/leads" className="text-primary-600 hover:text-primary-700 text-sm">
            ← Back to leads
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/leads')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeftIcon className="h-5 w-5 text-gray-500" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {lead.name || 'Unknown Lead'}
            </h1>
            <p className="text-gray-500">{lead.phone_number}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <LeadScoreBadge score={lead.score} />
          <a
            href={`tel:${lead.phone_number}`}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium text-sm inline-flex items-center"
          >
            <PhoneIcon className="h-4 w-4 mr-2" />
            Call
          </a>
          {lead.email && (
            <a
              href={`mailto:${lead.email}`}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium text-sm inline-flex items-center"
            >
              <EnvelopeIcon className="h-4 w-4 mr-2" />
              Email
            </a>
          )}
          <button
            onClick={() => updateLeadMutation.mutate({ status: 'handed_off' })}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium text-sm inline-flex items-center"
          >
            <CheckCircleIcon className="h-4 w-4 mr-2" />
            Mark as Handed Off
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
        {/* Lead Info Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 overflow-y-auto">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Lead Information</h2>

          <div className="space-y-1 divide-y divide-gray-100">
            <InfoItem icon={UserIcon} label="Name" value={lead.name} />
            <InfoItem icon={PhoneIcon} label="Phone" value={lead.phone_number} />
            <InfoItem icon={EnvelopeIcon} label="Email" value={lead.email} />
            <InfoItem icon={MapPinIcon} label="Location" value={lead.location} />
            <InfoItem icon={BriefcaseIcon} label="Service Interest" value={lead.service_interest} />
            <InfoItem icon={CurrencyDollarIcon} label="Budget" value={lead.budget} />
            <InfoItem icon={ClockIcon} label="Timeline" value={lead.timeline} />
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Status History</h3>
            <div className="space-y-3">
              <div className="flex items-center text-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                <span className="text-gray-600">
                  Current: {lead.status.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="flex items-center text-sm">
                <div className="w-2 h-2 bg-gray-300 rounded-full mr-2"></div>
                <span className="text-gray-500">
                  Created: {new Date(lead.created_at).toLocaleDateString()}
                </span>
              </div>
              {lead.last_contact_at && (
                <div className="flex items-center text-sm">
                  <div className="w-2 h-2 bg-gray-300 rounded-full mr-2"></div>
                  <span className="text-gray-500">
                    Last Contact: {new Date(lead.last_contact_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Qualification Data</h3>
            {lead.qualification_data ? (
              <pre className="text-xs bg-gray-50 p-3 rounded-lg overflow-x-auto">
                {JSON.stringify(lead.qualification_data, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-gray-500">No qualification data yet</p>
            )}
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => updateLeadMutation.mutate({ score: 'hot' })}
                className="w-full px-3 py-2 text-left text-sm bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors"
              >
                🔥 Mark as Hot
              </button>
              <button
                onClick={() => updateLeadMutation.mutate({ score: 'warm' })}
                className="w-full px-3 py-2 text-left text-sm bg-amber-50 text-amber-700 rounded-lg hover:bg-amber-100 transition-colors"
              >
                ☀️ Mark as Warm
              </button>
              <button
                onClick={() => updateLeadMutation.mutate({ score: 'cold' })}
                className="w-full px-3 py-2 text-left text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
              >
                ❄️ Mark as Cold
              </button>
            </div>
          </div>
        </div>

        {/* Conversation Panel */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col min-h-[500px]">
          {conversationsLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : conversations && conversations.length > 0 ? (
            <>
              {/* Conversation Tabs */}
              {conversations.length > 1 && (
                <div className="flex space-x-1 p-2 border-b border-gray-200 bg-gray-50 rounded-t-xl overflow-x-auto">
                  {conversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => setActiveConversationId(conv.id)}
                      className={`px-3 py-1.5 text-sm rounded-lg whitespace-nowrap ${
                        (activeConversation?.id || conversations[0].id) === conv.id
                          ? 'bg-white text-primary-700 shadow-sm'
                          : 'text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {conv.channel === 'whatsapp' ? '💬 WhatsApp' : '📱 SMS'}
                      {conv.human_takeover && ' (Human)'}
                    </button>
                  ))}
                </div>
              )}

              {/* Active Conversation */}
              {activeConversation && (
                <ConversationPanel
                  conversation={activeConversation}
                  clientId={clientId}
                />
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <ChatBubbleLeftRightIcon className="h-12 w-12 text-gray-300 mx-auto" />
                <p className="mt-2 text-gray-500">No conversations yet</p>
                <p className="text-sm text-gray-400">
                  Conversations will appear when the lead contacts you
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
