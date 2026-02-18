// Escalations Page - Monitor and resolve escalated conversations

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { format, formatDistanceToNow } from 'date-fns';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  ChatBubbleLeftRightIcon,
  UserIcon,
  PhoneIcon,
  EnvelopeIcon,
  FireIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { useClientStore, useAuthStore } from '../store';
import { escalationsApi } from '../api';
import type { Escalation } from '../types';

function StatCard({ title, value, icon: Icon, color }: {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
        </div>
        <div className={clsx('rounded-lg p-2.5',
          color === 'red' && 'bg-red-100 text-red-600',
          color === 'green' && 'bg-green-100 text-green-600',
          color === 'yellow' && 'bg-yellow-100 text-yellow-600',
          color === 'blue' && 'bg-blue-100 text-blue-600',
        )}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function EscalationSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-5">
          <div className="space-y-3">
            <div className="h-4 w-40 bg-gray-200 rounded" />
            <div className="h-3 w-60 bg-gray-200 rounded" />
            <div className="h-3 w-32 bg-gray-200 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function EscalationsPage() {
  const { currentClient } = useClientStore();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [showResolved, setShowResolved] = useState(false);

  const { data: escalations, isLoading } = useQuery({
    queryKey: ['escalations', currentClient?.id, showResolved],
    queryFn: () => escalationsApi.list(currentClient!.id, showResolved),
    enabled: !!currentClient?.id,
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) =>
      escalationsApi.resolve(id, user?.email || 'admin'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escalations'] });
      toast.success('Escalation resolved');
    },
    onError: () => {
      toast.error('Failed to resolve escalation');
    },
  });

  const pending = escalations?.filter((e: Escalation) => !e.resolved_at) || [];
  const resolved = escalations?.filter((e: Escalation) => e.resolved_at) || [];

  const reasonCounts: Record<string, number> = {};
  (escalations || []).forEach((e: Escalation) => {
    reasonCounts[e.reason] = (reasonCounts[e.reason] || 0) + 1;
  });

  if (!currentClient) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a client to view escalations.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Escalations</h1>
        <p className="text-sm text-gray-500 mt-1">Monitor and resolve escalated conversations that need human attention</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Escalations" value={escalations?.length || 0} icon={ExclamationTriangleIcon} color="red" />
        <StatCard title="Pending" value={pending.length} icon={ClockIcon} color="yellow" />
        <StatCard title="Resolved" value={resolved.length} icon={CheckCircleIcon} color="green" />
        <StatCard title="Most Common Reason" value={Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'} icon={FunnelIcon} color="blue" />
      </div>

      {/* Filter toggle */}
      <div className="flex items-center justify-between">
        <div className="flex rounded-lg border border-gray-300 overflow-hidden">
          <button
            onClick={() => setShowResolved(false)}
            className={clsx(
              'px-4 py-2 text-sm font-medium transition-colors',
              !showResolved ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            )}
          >
            Pending ({pending.length})
          </button>
          <button
            onClick={() => setShowResolved(true)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-l border-gray-300 transition-colors',
              showResolved ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            )}
          >
            Resolved ({resolved.length})
          </button>
        </div>
      </div>

      {/* Escalation list */}
      {isLoading ? (
        <EscalationSkeleton />
      ) : !escalations || escalations.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <CheckCircleIcon className="mx-auto h-12 w-12 text-green-300" />
          <p className="mt-3 text-sm font-medium text-gray-900">
            {showResolved ? 'No resolved escalations' : 'No pending escalations'}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {showResolved ? 'Resolved escalations will appear here' : 'Great! All escalations have been handled.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {escalations.map((escalation: Escalation) => (
            <div
              key={escalation.id}
              className={clsx(
                'bg-white rounded-xl border p-5 transition-shadow hover:shadow-sm',
                !escalation.resolved_at ? 'border-red-200' : 'border-gray-200'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={clsx(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      !escalation.resolved_at ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                    )}>
                      {!escalation.resolved_at ? '⚠ Pending' : '✓ Resolved'}
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      {escalation.reason}
                    </span>
                    {escalation.conversation_channel && (
                      <span className="text-xs text-gray-400 capitalize">{escalation.conversation_channel}</span>
                    )}
                  </div>

                  {escalation.reason_details && (
                    <p className="text-sm text-gray-700 mb-3">{escalation.reason_details}</p>
                  )}

                  {/* Lead info */}
                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                    {escalation.lead_name && (
                      <span className="flex items-center gap-1">
                        <UserIcon className="h-4 w-4" />
                        <Link to={`/leads/${escalation.lead_id}`} className="text-blue-600 hover:underline">
                          {escalation.lead_name}
                        </Link>
                      </span>
                    )}
                    {escalation.lead_phone && (
                      <span className="flex items-center gap-1">
                        <PhoneIcon className="h-4 w-4" />
                        {escalation.lead_phone}
                      </span>
                    )}
                    {escalation.lead_email && (
                      <span className="flex items-center gap-1">
                        <EnvelopeIcon className="h-4 w-4" />
                        {escalation.lead_email}
                      </span>
                    )}
                    {escalation.lead_score && (
                      <span className={clsx('flex items-center gap-1',
                        escalation.lead_score === 'hot' && 'text-red-600',
                        escalation.lead_score === 'warm' && 'text-yellow-600',
                        escalation.lead_score === 'cold' && 'text-blue-600',
                      )}>
                        <FireIcon className="h-4 w-4" />
                        {escalation.lead_score}
                      </span>
                    )}
                    {escalation.message_count != null && (
                      <span className="flex items-center gap-1">
                        <ChatBubbleLeftRightIcon className="h-4 w-4" />
                        {escalation.message_count} msgs
                      </span>
                    )}
                  </div>

                  {/* Timestamps */}
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                    <span>Escalated {formatDistanceToNow(new Date(escalation.created_at), { addSuffix: true })}</span>
                    {escalation.resolved_at && (
                      <span>Resolved {format(new Date(escalation.resolved_at), 'MMM d, h:mm a')} by {escalation.resolved_by}</span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                  <Link
                    to={`/conversations/${escalation.conversation_id}`}
                    className="px-3 py-1.5 text-sm font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
                  >
                    View Chat
                  </Link>
                  {!escalation.resolved_at && (
                    <button
                      onClick={() => resolveMutation.mutate(escalation.id)}
                      disabled={resolveMutation.isPending}
                      className="px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {resolveMutation.isPending ? 'Resolving...' : 'Resolve'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
