// Escalations Management Page

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format, parseISO, formatDistanceToNow } from 'date-fns';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ChatBubbleLeftRightIcon,
  PhoneIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import type { Escalation, Lead, Conversation, EscalationReason } from '../types';

// Mock data
interface EscalationWithDetails extends Escalation {
  lead: Lead;
  conversation: Conversation;
}

const mockEscalations: EscalationWithDetails[] = [
  {
    id: '1',
    client_id: '1',
    conversation_id: '2',
    lead_id: '2',
    reason: 'lead_request',
    reason_details: 'Lead explicitly asked to speak with a human representative',
    resolved_at: null,
    resolved_by: null,
    created_at: new Date(Date.now() - 300000).toISOString(),
    lead: {
      id: '2',
      client_id: '1',
      name: 'Sarah Johnson',
      phone: '+14155551234',
      email: 'sarah@example.com',
      score: 'warm',
      status: 'qualifying',
    } as Lead,
    conversation: {
      id: '2',
      client_id: '1',
      lead_id: '2',
      channel: 'sms',
      is_active: true,
      is_escalated: true,
      message_count: 12,
    } as Conversation,
  },
  {
    id: '2',
    client_id: '1',
    conversation_id: '5',
    lead_id: '5',
    reason: 'negative_sentiment',
    reason_details: 'Detected frustration in lead responses',
    resolved_at: null,
    resolved_by: null,
    created_at: new Date(Date.now() - 900000).toISOString(),
    lead: {
      id: '5',
      client_id: '1',
      name: 'Omar Al-Farsi',
      phone: '+966559876543',
      email: 'omar@company.com',
      score: 'hot',
      status: 'qualifying',
    } as Lead,
    conversation: {
      id: '5',
      client_id: '1',
      lead_id: '5',
      channel: 'whatsapp',
      is_active: true,
      is_escalated: true,
      message_count: 8,
    } as Conversation,
  },
  {
    id: '3',
    client_id: '1',
    conversation_id: '3',
    lead_id: '3',
    reason: 'low_confidence',
    reason_details: 'AI confidence dropped below threshold after complex query',
    resolved_at: new Date(Date.now() - 1800000).toISOString(),
    resolved_by: 'admin@example.com',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    lead: {
      id: '3',
      client_id: '1',
      name: 'Mohammed Hassan',
      phone: '+966551234567',
      email: 'mhassan@company.com',
      score: 'cold',
      status: 'nurturing',
    } as Lead,
    conversation: {
      id: '3',
      client_id: '1',
      lead_id: '3',
      channel: 'web_form',
      is_active: false,
      is_escalated: false,
      message_count: 6,
    } as Conversation,
  },
];

const REASON_LABELS: Record<EscalationReason, { label: string; color: string }> = {
  lead_request: { label: 'Lead Requested Human', color: 'bg-blue-100 text-blue-700' },
  low_confidence: { label: 'Low AI Confidence', color: 'bg-yellow-100 text-yellow-700' },
  high_value: { label: 'High Value Lead', color: 'bg-purple-100 text-purple-700' },
  long_conversation: { label: 'Long Conversation', color: 'bg-gray-100 text-gray-700' },
  negative_sentiment: { label: 'Negative Sentiment', color: 'bg-red-100 text-red-700' },
  agent_error: { label: 'Agent Error', color: 'bg-orange-100 text-orange-700' },
};

function EscalationCard({
  escalation,
  onResolve,
}: {
  escalation: EscalationWithDetails;
  onResolve: (id: string) => void;
}) {
  const isResolved = !!escalation.resolved_at;
  const reasonInfo = REASON_LABELS[escalation.reason];

  return (
    <div
      className={clsx(
        'bg-white rounded-xl shadow-sm border p-6',
        isResolved ? 'border-gray-200' : 'border-yellow-300'
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              'h-10 w-10 rounded-full flex items-center justify-center',
              isResolved ? 'bg-green-100' : 'bg-yellow-100'
            )}
          >
            {isResolved ? (
              <CheckCircleIcon className="h-6 w-6 text-green-600" />
            ) : (
              <ExclamationTriangleIcon className="h-6 w-6 text-yellow-600" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{escalation.lead.name}</h3>
            <p className="text-sm text-gray-500">
              {formatDistanceToNow(parseISO(escalation.created_at), { addSuffix: true })}
            </p>
          </div>
        </div>
        <span
          className={clsx(
            'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
            reasonInfo.color
          )}
        >
          {reasonInfo.label}
        </span>
      </div>

      {escalation.reason_details && (
        <p className="text-sm text-gray-600 mb-4 bg-gray-50 rounded-lg p-3">
          {escalation.reason_details}
        </p>
      )}

      <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
        <span className="flex items-center gap-1">
          <ChatBubbleLeftRightIcon className="h-4 w-4" />
          {escalation.conversation.channel.replace('_', ' ')}
        </span>
        <span className="flex items-center gap-1">
          <UserIcon className="h-4 w-4" />
          {escalation.conversation.message_count} messages
        </span>
        {escalation.lead.phone && (
          <a
            href={`tel:${escalation.lead.phone}`}
            className="flex items-center gap-1 text-blue-600 hover:text-blue-800"
          >
            <PhoneIcon className="h-4 w-4" />
            {escalation.lead.phone}
          </a>
        )}
      </div>

      {isResolved ? (
        <div className="text-sm text-gray-500 pt-4 border-t">
          <p>
            Resolved by <span className="font-medium">{escalation.resolved_by}</span>
          </p>
          <p>
            {format(parseISO(escalation.resolved_at!), 'MMM d, yyyy h:mm a')}
          </p>
        </div>
      ) : (
        <div className="flex items-center gap-3 pt-4 border-t">
          <Link
            to={`/conversations?id=${escalation.conversation_id}`}
            className="flex-1 inline-flex items-center justify-center gap-2 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            <ChatBubbleLeftRightIcon className="h-4 w-4" />
            View Conversation
          </Link>
          <button
            onClick={() => onResolve(escalation.id)}
            className="flex-1 inline-flex items-center justify-center gap-2 py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
          >
            <CheckCircleIcon className="h-4 w-4" />
            Mark Resolved
          </button>
        </div>
      )}
    </div>
  );
}

export default function EscalationsPage() {
  const [escalations, setEscalations] = useState(mockEscalations);
  const [filter, setFilter] = useState<'pending' | 'resolved' | 'all'>('pending');

  const filteredEscalations = escalations.filter((e) => {
    if (filter === 'pending') return !e.resolved_at;
    if (filter === 'resolved') return !!e.resolved_at;
    return true;
  });

  const pendingCount = escalations.filter((e) => !e.resolved_at).length;

  const handleResolve = (id: string) => {
    setEscalations(
      escalations.map((e) =>
        e.id === id
          ? {
              ...e,
              resolved_at: new Date().toISOString(),
              resolved_by: 'admin@example.com',
            }
          : e
      )
    );
    toast.success('Escalation marked as resolved');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Escalations</h1>
          <p className="text-gray-500">
            {pendingCount} pending escalation{pendingCount !== 1 ? 's' : ''} requiring attention
          </p>
        </div>
      </div>

      {/* Alert Banner */}
      {pendingCount > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-center gap-4">
          <ExclamationTriangleIcon className="h-8 w-8 text-yellow-500 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-yellow-800">Attention Required</h3>
            <p className="text-sm text-yellow-700">
              You have {pendingCount} conversation{pendingCount !== 1 ? 's' : ''} that need human
              intervention. Respond promptly to maintain customer satisfaction.
            </p>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {(['pending', 'resolved', 'all'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              filter === f
                ? 'bg-gray-900 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            )}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f === 'pending' && pendingCount > 0 && (
              <span className="ml-2 inline-flex items-center justify-center h-5 w-5 rounded-full bg-yellow-400 text-yellow-900 text-xs">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Escalations List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredEscalations.map((escalation) => (
          <EscalationCard
            key={escalation.id}
            escalation={escalation}
            onResolve={handleResolve}
          />
        ))}
      </div>

      {filteredEscalations.length === 0 && (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <CheckCircleIcon className="h-12 w-12 mx-auto text-green-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {filter === 'pending' ? 'All caught up!' : 'No escalations found'}
          </h3>
          <p className="text-gray-500">
            {filter === 'pending'
              ? 'There are no pending escalations requiring your attention.'
              : 'Try adjusting your filter to see different escalations.'}
          </p>
        </div>
      )}
    </div>
  );
}
