// Conversations Page with Chat Viewer

import { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { format, parseISO, formatDistanceToNow } from 'date-fns';
import { clsx } from 'clsx';
import {
  ChatBubbleLeftRightIcon,
  UserCircleIcon,
  CpuChipIcon,
  UserIcon,
  ExclamationTriangleIcon,
  PaperAirplaneIcon,
  PhoneIcon,
  XMarkIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';
import type { Conversation, Message, Lead, ChannelType } from '../types';

// Mock data
const mockConversations: (Conversation & { lead: Lead })[] = [
  {
    id: '1',
    client_id: '1',
    lead_id: '1',
    channel: 'whatsapp',
    session_id: 'sess_001',
    is_active: true,
    is_escalated: false,
    message_count: 8,
    created_at: new Date(Date.now() - 1800000).toISOString(),
    updated_at: new Date(Date.now() - 60000).toISOString(),
    lead: {
      id: '1',
      client_id: '1',
      name: 'Ahmed Al-Rashid',
      phone: '+966501234567',
      email: 'ahmed@example.com',
      score: 'hot',
      status: 'qualifying',
    } as Lead,
  },
  {
    id: '2',
    client_id: '1',
    lead_id: '2',
    channel: 'sms',
    session_id: 'sess_002',
    is_active: true,
    is_escalated: true,
    escalation_reason: 'lead_request',
    escalation_details: 'Lead requested to speak with human',
    escalated_at: new Date(Date.now() - 300000).toISOString(),
    message_count: 12,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date(Date.now() - 300000).toISOString(),
    lead: {
      id: '2',
      client_id: '1',
      name: 'Sarah Johnson',
      phone: '+14155551234',
      email: 'sarah@example.com',
      score: 'warm',
      status: 'qualifying',
    } as Lead,
  },
  {
    id: '3',
    client_id: '1',
    lead_id: '3',
    channel: 'web_form',
    session_id: 'sess_003',
    is_active: false,
    is_escalated: false,
    message_count: 6,
    ended_at: new Date(Date.now() - 7200000).toISOString(),
    summary: 'Lead inquired about rental properties. Cold lead, exploring options.',
    created_at: new Date(Date.now() - 10800000).toISOString(),
    updated_at: new Date(Date.now() - 7200000).toISOString(),
    lead: {
      id: '3',
      client_id: '1',
      name: 'Mohammed Hassan',
      phone: '+966551234567',
      email: 'mhassan@company.com',
      score: 'cold',
      status: 'nurturing',
    } as Lead,
  },
];

const mockMessages: Record<string, Message[]> = {
  '1': [
    {
      id: 'm1',
      conversation_id: '1',
      role: 'lead',
      content: 'Hi, I saw your listing for the villa in Riyadh. Is it still available?',
      tokens_input: 0,
      tokens_output: 0,
      created_at: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      id: 'm2',
      conversation_id: '1',
      role: 'agent',
      content: "Hello Ahmed! 👋 Yes, the villa is still available. It's a beautiful 4-bedroom property in the Al-Nakheel district. Are you looking for a primary residence or an investment property?",
      tokens_input: 45,
      tokens_output: 52,
      model_used: 'claude-sonnet-4-20250514',
      confidence_score: 0.92,
      intent: 'gather_info',
      created_at: new Date(Date.now() - 1750000).toISOString(),
    },
    {
      id: 'm3',
      conversation_id: '1',
      role: 'lead',
      content: "Primary residence. I'm looking to move my family there. What's the price and can I schedule a viewing?",
      tokens_input: 0,
      tokens_output: 0,
      created_at: new Date(Date.now() - 1500000).toISOString(),
    },
    {
      id: 'm4',
      conversation_id: '1',
      role: 'agent',
      content: "Perfect! The villa is listed at 1.1M SAR. It features 4 bedrooms, a private garden, and is close to international schools. I'd be happy to schedule a viewing for you. What days work best for you this week?",
      tokens_input: 68,
      tokens_output: 58,
      model_used: 'claude-sonnet-4-20250514',
      confidence_score: 0.95,
      intent: 'book_appointment',
      created_at: new Date(Date.now() - 1400000).toISOString(),
    },
    {
      id: 'm5',
      conversation_id: '1',
      role: 'lead',
      content: 'This Thursday afternoon would be great. Around 3 PM?',
      tokens_input: 0,
      tokens_output: 0,
      created_at: new Date(Date.now() - 300000).toISOString(),
    },
    {
      id: 'm6',
      conversation_id: '1',
      role: 'agent',
      content: "Thursday at 3 PM works perfectly! I've noted your interest. Our property specialist will confirm the viewing shortly. Is there anything specific you'd like to know before the visit?",
      tokens_input: 72,
      tokens_output: 48,
      model_used: 'claude-sonnet-4-20250514',
      confidence_score: 0.94,
      intent: 'confirm_appointment',
      created_at: new Date(Date.now() - 60000).toISOString(),
    },
  ],
  '2': [
    {
      id: 'm7',
      conversation_id: '2',
      role: 'lead',
      content: 'I need to rent a 2-bedroom apartment',
      tokens_input: 0,
      tokens_output: 0,
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: 'm8',
      conversation_id: '2',
      role: 'agent',
      content: "Hi Sarah! I'd love to help you find the perfect 2-bedroom apartment. What area are you looking in, and what's your monthly budget?",
      tokens_input: 32,
      tokens_output: 38,
      model_used: 'claude-sonnet-4-20250514',
      confidence_score: 0.88,
      created_at: new Date(Date.now() - 3500000).toISOString(),
    },
    {
      id: 'm9',
      conversation_id: '2',
      role: 'lead',
      content: 'Actually, can I speak to a real person? I have some specific requirements.',
      tokens_input: 0,
      tokens_output: 0,
      created_at: new Date(Date.now() - 600000).toISOString(),
    },
    {
      id: 'm10',
      conversation_id: '2',
      role: 'agent',
      content: "Of course! I completely understand. Let me connect you with one of our property specialists who can give you personalized attention. They'll reach out to you shortly. Is there anything else I can help with in the meantime?",
      tokens_input: 45,
      tokens_output: 52,
      model_used: 'claude-sonnet-4-20250514',
      confidence_score: 0.96,
      intent: 'escalate_to_human',
      created_at: new Date(Date.now() - 300000).toISOString(),
    },
  ],
};

function ChannelIcon({ channel }: { channel: ChannelType }) {
  const icons: Record<ChannelType, string> = {
    whatsapp: '💬',
    sms: '📱',
    web_form: '🌐',
    live_chat: '💭',
    missed_call: '📞',
    voice: '🎤',
    email: '✉️',
  };
  return <span>{icons[channel] || '💬'}</span>;
}

function MessageBubble({ message }: { message: Message }) {
  const isLead = message.role === 'lead';
  const isAgent = message.role === 'agent';
  const isHuman = message.role === 'human';
  const isSystem = message.role === 'system';

  return (
    <div
      className={clsx(
        'flex gap-3 max-w-3xl',
        isLead ? 'ml-auto flex-row-reverse' : ''
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center',
          isLead && 'bg-blue-100 text-blue-600',
          isAgent && 'bg-purple-100 text-purple-600',
          isHuman && 'bg-green-100 text-green-600',
          isSystem && 'bg-gray-100 text-gray-600'
        )}
      >
        {isLead && <UserCircleIcon className="h-5 w-5" />}
        {isAgent && <CpuChipIcon className="h-5 w-5" />}
        {isHuman && <UserIcon className="h-5 w-5" />}
        {isSystem && <ExclamationTriangleIcon className="h-5 w-5" />}
      </div>

      {/* Message */}
      <div className={clsx('flex-1', isLead && 'text-right')}>
        <div
          className={clsx(
            'inline-block rounded-2xl px-4 py-2 max-w-lg text-left',
            isLead && 'bg-blue-600 text-white',
            isAgent && 'bg-gray-100 text-gray-900',
            isHuman && 'bg-green-100 text-gray-900',
            isSystem && 'bg-yellow-50 text-yellow-800 border border-yellow-200'
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div
          className={clsx(
            'mt-1 flex items-center gap-2 text-xs text-gray-500',
            isLead && 'justify-end'
          )}
        >
          <span>{format(parseISO(message.created_at), 'h:mm a')}</span>
          {isAgent && message.confidence_score && (
            <span className="text-purple-600">
              {Math.round(message.confidence_score * 100)}% confidence
            </span>
          )}
          {isAgent && message.model_used && (
            <span className="text-gray-400">{message.model_used.split('-')[0]}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function ConversationList({
  conversations,
  selectedId,
  onSelect,
}: {
  conversations: (Conversation & { lead: Lead })[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="space-y-2">
      {conversations.map((conv) => (
        <button
          key={conv.id}
          onClick={() => onSelect(conv.id)}
          className={clsx(
            'w-full text-left p-4 rounded-lg border transition-colors',
            selectedId === conv.id
              ? 'bg-blue-50 border-blue-200'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          )}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <ChannelIcon channel={conv.channel} />
              <span className="font-medium text-gray-900">
                {conv.lead?.name || 'Unknown'}
              </span>
              {conv.is_escalated && (
                <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                  Escalated
                </span>
              )}
            </div>
            <span
              className={clsx(
                'h-2 w-2 rounded-full',
                conv.is_active ? 'bg-green-500' : 'bg-gray-300'
              )}
            />
          </div>
          <p className="mt-1 text-sm text-gray-500 truncate">
            {conv.summary || `${conv.message_count} messages`}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            {formatDistanceToNow(parseISO(conv.updated_at), { addSuffix: true })}
          </p>
        </button>
      ))}
    </div>
  );
}

function ChatView({
  conversation,
  messages,
  onSendMessage,
  onClose,
}: {
  conversation: Conversation & { lead: Lead };
  messages: Message[];
  onSendMessage: (content: string) => void;
  onClose: () => void;
}) {
  const [newMessage, setNewMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (newMessage.trim()) {
      onSendMessage(newMessage.trim());
      setNewMessage('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <div className="flex items-center gap-3">
          <ChannelIcon channel={conversation.channel} />
          <div>
            <h3 className="font-semibold text-gray-900">
              {conversation.lead?.name || 'Unknown Lead'}
            </h3>
            <p className="text-sm text-gray-500">
              {conversation.lead?.phone || conversation.lead?.email}
            </p>
          </div>
          {conversation.is_escalated && (
            <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-700">
              <ExclamationTriangleIcon className="h-4 w-4" />
              Escalated
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {conversation.lead?.phone && (
            <a
              href={`tel:${conversation.lead.phone}`}
              className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
            >
              <PhoneIcon className="h-4 w-4" />
              Call
            </a>
          )}
          <Link
            to={`/leads/${conversation.lead_id}`}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            View Lead
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-2 text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      {conversation.is_active && (
        <div className="p-4 border-t bg-white">
          <div className="flex gap-2">
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type a message as human agent..."
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={handleSend}
              disabled={!newMessage.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PaperAirplaneIcon className="h-5 w-5" />
              Send
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Sending as human agent. AI will pause for this conversation.
          </p>
        </div>
      )}

      {!conversation.is_active && (
        <div className="p-4 border-t bg-gray-100 text-center text-gray-500">
          This conversation has ended
        </div>
      )}
    </div>
  );
}

export default function ConversationsPage() {
  const [searchParams] = useSearchParams();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'escalated'>(
    searchParams.get('filter') as 'all' | 'active' | 'escalated' || 'all'
  );

  const filteredConversations = mockConversations.filter((conv) => {
    if (filter === 'active') return conv.is_active;
    if (filter === 'escalated') return conv.is_escalated;
    return true;
  });

  const selectedConversation = selectedId
    ? mockConversations.find((c) => c.id === selectedId)
    : null;
  const selectedMessages = selectedId ? mockMessages[selectedId] || [] : [];

  const handleSendMessage = (content: string) => {
    console.log('Send message:', content);
    // In production, call API to send message
  };

  return (
    <div className="h-[calc(100vh-8rem)]">
      <div className="flex flex-col lg:flex-row h-full gap-6">
        {/* Conversation List */}
        <div
          className={clsx(
            'lg:w-96 flex-shrink-0 flex flex-col',
            selectedConversation && 'hidden lg:flex'
          )}
        >
          {/* Header */}
          <div className="mb-4">
            <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
            <p className="text-gray-500">{filteredConversations.length} conversations</p>
          </div>

          {/* Filter Tabs */}
          <div className="flex gap-2 mb-4">
            {(['all', 'active', 'escalated'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  filter === f
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                )}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
                {f === 'escalated' && (
                  <span className="ml-1.5 inline-flex items-center justify-center h-5 w-5 rounded-full bg-yellow-400 text-yellow-900 text-xs">
                    {mockConversations.filter((c) => c.is_escalated).length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            <ConversationList
              conversations={filteredConversations}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
            {filteredConversations.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                No conversations found
              </div>
            )}
          </div>
        </div>

        {/* Chat View */}
        <div
          className={clsx(
            'flex-1 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden',
            !selectedConversation && 'hidden lg:flex items-center justify-center'
          )}
        >
          {selectedConversation ? (
            <ChatView
              conversation={selectedConversation}
              messages={selectedMessages}
              onSendMessage={handleSendMessage}
              onClose={() => setSelectedId(null)}
            />
          ) : (
            <div className="text-center text-gray-500">
              <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a conversation to view</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
