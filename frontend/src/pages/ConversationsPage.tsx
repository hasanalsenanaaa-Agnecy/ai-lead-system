// Conversations Page - View and manage AI conversations with leads

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { format } from 'date-fns';
import { clsx } from 'clsx';
import {
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  UserCircleIcon,
  CpuChipIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';
import { conversationsApi } from '../api';
import type { Conversation, Message } from '../types';

const CHANNEL_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  web_form: { label: 'Web', color: 'text-blue-700', bg: 'bg-blue-100' },
  sms: { label: 'SMS', color: 'text-green-700', bg: 'bg-green-100' },
  whatsapp: { label: 'WhatsApp', color: 'text-emerald-700', bg: 'bg-emerald-100' },
  voice: { label: 'Voice', color: 'text-purple-700', bg: 'bg-purple-100' },
  live_chat: { label: 'Live Chat', color: 'text-indigo-700', bg: 'bg-indigo-100' },
  email: { label: 'Email', color: 'text-orange-700', bg: 'bg-orange-100' },
  missed_call: { label: 'Missed Call', color: 'text-red-700', bg: 'bg-red-100' },
};

type FilterType = 'all' | 'active' | 'escalated' | 'ended';

function ConversationSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-2 flex-1">
              <div className="h-4 w-32 bg-gray-200 rounded" />
              <div className="h-3 w-48 bg-gray-200 rounded" />
            </div>
            <div className="h-6 w-16 bg-gray-200 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isAgent = message.role === 'agent' || message.role === 'system';
  const isHuman = message.role === 'human';

  return (
    <div className={clsx('flex mb-4', isAgent ? 'justify-start' : 'justify-end')}>
      <div className="max-w-[75%]">
        <div className="flex items-center gap-1.5 mb-1">
          {isAgent ? (
            <CpuChipIcon className="h-4 w-4 text-blue-500" />
          ) : isHuman ? (
            <UserCircleIcon className="h-4 w-4 text-purple-500" />
          ) : (
            <UserCircleIcon className="h-4 w-4 text-gray-500" />
          )}
          <span className="text-xs font-medium text-gray-500 capitalize">{message.role}</span>
          <span className="text-xs text-gray-400">
            {format(new Date(message.created_at), 'h:mm a')}
          </span>
        </div>
        <div
          className={clsx(
            'rounded-2xl px-4 py-2.5 text-sm',
            isAgent
              ? 'bg-gray-100 text-gray-900 rounded-tl-sm'
              : isHuman
              ? 'bg-purple-100 text-purple-900 rounded-tr-sm'
              : 'bg-blue-600 text-white rounded-tr-sm'
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.confidence_score != null && (
          <p className="text-xs text-gray-400 mt-1">
            Confidence: {(message.confidence_score * 100).toFixed(0)}%
            {message.processing_time_ms ? ` · ${message.processing_time_ms}ms` : ''}
          </p>
        )}
      </div>
    </div>
  );
}

export default function ConversationsPage() {
  const { id: selectedId } = useParams();
  const { currentClient } = useClientStore();
  const [filter, setFilter] = useState<FilterType>('all');
  const [search, setSearch] = useState('');
  const [selectedConversation, setSelectedConversation] = useState<string | null>(selectedId || null);

  const { data: conversationsData, isLoading: loadingConversations } = useQuery({
    queryKey: ['conversations', currentClient?.id, filter],
    queryFn: async () => {
      if (!currentClient?.id) return { items: [] as Conversation[], total: 0 };
      if (filter === 'active') {
        const result = await conversationsApi.getActive(currentClient.id);
        const items = Array.isArray(result) ? result : result.items ?? [];
        return { items, total: items.length };
      }
      if (filter === 'escalated') {
        const result = await conversationsApi.getEscalated(currentClient.id);
        const items = Array.isArray(result) ? result : result.items ?? [];
        return { items, total: items.length };
      }
      const filters = filter === 'ended' ? { is_active: false as const } : undefined;
      const result = await conversationsApi.list(currentClient.id, filters, 1, 50);
      return { items: (result.items || []) as Conversation[], total: result.total || 0 };
    },
    enabled: !!currentClient?.id,
  });

  const { data: messages, isLoading: loadingMessages } = useQuery({
    queryKey: ['conversation-messages', selectedConversation],
    queryFn: () => conversationsApi.getMessages(selectedConversation!, 100),
    enabled: !!selectedConversation,
  });

  const { data: conversationDetail } = useQuery({
    queryKey: ['conversation-detail', selectedConversation],
    queryFn: () => conversationsApi.get(selectedConversation!),
    enabled: !!selectedConversation,
  });

  console.log('conversationsData', conversationsData);
  const conversations = conversationsData?.items ?? [];
  const filteredConversations = conversations.filter((c) => {
    if (!search) return true;
    return (
      c.channel.toLowerCase().includes(search.toLowerCase()) ||
      c.summary?.toLowerCase().includes(search.toLowerCase()) ||
      c.id.includes(search)
    );
  });

  if (!currentClient) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a client to view conversations.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
          <p className="text-sm text-gray-500 mt-1">
            {conversationsData?.total || 0} conversation{(conversationsData?.total || 0) !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <XMarkIcon className="h-4 w-4 text-gray-400 hover:text-gray-600" />
            </button>
          )}
        </div>
        <div className="flex rounded-lg border border-gray-300 overflow-hidden">
          {(['all', 'active', 'escalated', 'ended'] as FilterType[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                'px-3 py-2 text-sm font-medium capitalize transition-colors',
                filter === f ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50',
                f !== 'all' && 'border-l border-gray-300'
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-4 h-[calc(100vh-16rem)]">
        {/* Conversation list */}
        <div className="w-full md:w-96 flex-shrink-0 overflow-y-auto space-y-2">
          {loadingConversations ? (
            <ConversationSkeleton />
          ) : filteredConversations.length === 0 ? (
            <div className="text-center py-12">
              <ChatBubbleLeftRightIcon className="mx-auto h-12 w-12 text-gray-300" />
              <p className="mt-2 text-sm text-gray-500">No conversations found</p>
            </div>
          ) : (
            filteredConversations.map((conversation) => {
              const ch = CHANNEL_CONFIG[conversation.channel] || { label: conversation.channel, color: 'text-gray-700', bg: 'bg-gray-100' };
              const isSelected = selectedConversation === conversation.id;
              return (
                <button
                  key={conversation.id}
                  onClick={() => setSelectedConversation(conversation.id)}
                  className={clsx(
                    'w-full text-left bg-white rounded-lg border p-4 transition-all hover:shadow-sm',
                    isSelected ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-200 hover:border-gray-300'
                  )}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={clsx('inline-flex px-2 py-0.5 rounded-full text-xs font-medium', ch.bg, ch.color)}>
                        {ch.label}
                      </span>
                      {conversation.is_escalated && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                          <ExclamationTriangleIcon className="h-3 w-3 mr-0.5" />
                          Escalated
                        </span>
                      )}
                    </div>
                    <span className={clsx('inline-flex h-2 w-2 rounded-full flex-shrink-0 mt-1', conversation.is_active ? 'bg-green-500' : 'bg-gray-300')} />
                  </div>
                  <p className="text-sm text-gray-900 font-medium truncate">
                    {conversation.summary || `Conversation #${conversation.id.slice(0, 8)}`}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <ChatBubbleLeftRightIcon className="h-3.5 w-3.5" />
                      {conversation.message_count} msgs
                    </span>
                    <span className="flex items-center gap-1">
                      <ClockIcon className="h-3.5 w-3.5" />
                      {format(new Date(conversation.created_at), 'MMM d, h:mm a')}
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Message thread */}
        <div className="hidden md:flex flex-col flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden">
          {selectedConversation && conversationDetail ? (
            <>
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">
                      {conversationDetail.summary || `Conversation #${conversationDetail.id.slice(0, 8)}`}
                    </h3>
                    <div className="flex items-center gap-3 mt-1">
                      <span className={clsx(
                        'inline-flex px-2 py-0.5 rounded-full text-xs font-medium',
                        CHANNEL_CONFIG[conversationDetail.channel]?.bg || 'bg-gray-100',
                        CHANNEL_CONFIG[conversationDetail.channel]?.color || 'text-gray-700'
                      )}>
                        {CHANNEL_CONFIG[conversationDetail.channel]?.label || conversationDetail.channel}
                      </span>
                      <span className={clsx('text-xs font-medium', conversationDetail.is_active ? 'text-green-600' : 'text-gray-400')}>
                        {conversationDetail.is_active ? '● Active' : '○ Ended'}
                      </span>
                      {conversationDetail.is_escalated && (
                        <span className="text-xs font-medium text-red-600 flex items-center gap-1">
                          <ExclamationTriangleIcon className="h-3.5 w-3.5" />
                          Escalated{conversationDetail.escalation_reason ? `: ${conversationDetail.escalation_reason}` : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <p>Started {format(new Date(conversationDetail.created_at), 'MMM d, yyyy h:mm a')}</p>
                    <p>{conversationDetail.message_count} messages</p>
                  </div>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-4">
                {loadingMessages ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                  </div>
                ) : messages && messages.length > 0 ? (
                  <div>
                    {messages.map((msg: Message) => (
                      <MessageBubble key={msg.id} message={msg} />
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <p>No messages in this conversation</p>
                  </div>
                )}
              </div>

              {conversationDetail.sentiment_score != null && (
                <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>
                      Sentiment:{' '}
                      <strong className={clsx(
                        conversationDetail.sentiment_score > 0.5 ? 'text-green-600' :
                        conversationDetail.sentiment_score < -0.5 ? 'text-red-600' : 'text-gray-600'
                      )}>
                        {conversationDetail.sentiment_score > 0.5 ? 'Positive' :
                         conversationDetail.sentiment_score < -0.5 ? 'Negative' : 'Neutral'}
                      </strong>
                    </span>
                    {conversationDetail.end_reason && (
                      <span>End reason: <strong>{conversationDetail.end_reason}</strong></span>
                    )}
                    <Link to={`/leads/${conversationDetail.lead_id}`} className="text-blue-600 hover:underline ml-auto">
                      View Lead →
                    </Link>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <ChatBubbleLeftRightIcon className="mx-auto h-12 w-12 text-gray-300" />
                <p className="mt-2 text-sm text-gray-500">Select a conversation to view messages</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
