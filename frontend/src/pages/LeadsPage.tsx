// Leads Management Page - Connected to Backend API

import { useState, useMemo } from 'react';
import { Link, useSearchParams, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  PhoneIcon,
  EnvelopeIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowPathIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  CalendarIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';
import { leadsApi, conversationsApi } from '../api';
import type { Lead, LeadScore, LeadStatus } from '../types';

const SCORE_COLORS: Record<LeadScore, string> = {
  hot: 'bg-red-100 text-red-700 border-red-200',
  warm: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  cold: 'bg-blue-100 text-blue-700 border-blue-200',
  unscored: 'bg-gray-100 text-gray-700 border-gray-200',
};

const STATUS_COLORS: Record<LeadStatus, string> = {
  new: 'bg-green-100 text-green-700',
  qualifying: 'bg-blue-100 text-blue-700',
  qualified: 'bg-purple-100 text-purple-700',
  appointment_booked: 'bg-indigo-100 text-indigo-700',
  handed_off: 'bg-orange-100 text-orange-700',
  nurturing: 'bg-cyan-100 text-cyan-700',
  closed_won: 'bg-emerald-100 text-emerald-700',
  closed_lost: 'bg-red-100 text-red-700',
  disqualified: 'bg-gray-100 text-gray-700',
};

const STATUS_LABELS: Record<LeadStatus, string> = {
  new: 'New',
  qualifying: 'Qualifying',
  qualified: 'Qualified',
  appointment_booked: 'Appointment Booked',
  handed_off: 'Handed Off',
  nurturing: 'Nurturing',
  closed_won: 'Won',
  closed_lost: 'Lost',
  disqualified: 'Disqualified',
};

function LeadDetailPanel({ lead, onClose }: { lead: Lead; onClose: () => void }) {
  const queryClient = useQueryClient();
  const { currentClient } = useClientStore();

  // Fetch conversations for this lead
  const { data: conversationsData } = useQuery({
    queryKey: ['lead-conversations', lead.id],
    queryFn: () => conversationsApi.list(currentClient?.id || '', { }, 1, 10),
    enabled: !!currentClient?.id,
  });

  // Update lead mutation
  const updateLeadMutation = useMutation({
    mutationFn: (updates: Partial<Lead>) => leadsApi.update(lead.id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead updated');
    },
    onError: () => {
      toast.error('Failed to update lead');
    },
  });

  // Handoff mutation
  const handoffMutation = useMutation({
    mutationFn: () => leadsApi.handoff(lead.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead handed off successfully');
    },
    onError: () => {
      toast.error('Failed to hand off lead');
    },
  });

  const conversations = conversationsData?.items?.filter(c => c.lead_id === lead.id) || [];

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-white shadow-xl border-l border-gray-200 z-50 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Lead Details</h2>
        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
          <XMarkIcon className="h-5 w-5 text-gray-500" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Contact Info */}
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
              <UserIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{lead.name || 'Unknown'}</h3>
              <p className="text-sm text-gray-500">{lead.service_interest || 'No service selected'}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center space-x-2 text-sm">
              <EnvelopeIcon className="h-4 w-4 text-gray-400" />
              <span className="text-gray-600">{lead.email || 'No email'}</span>
            </div>
            <div className="flex items-center space-x-2 text-sm">
              <PhoneIcon className="h-4 w-4 text-gray-400" />
              <span className="text-gray-600">{lead.phone || 'No phone'}</span>
            </div>
          </div>
        </div>

        {/* Score & Status */}
        <div className="flex items-center space-x-3">
          <span className={clsx('px-3 py-1 rounded-full text-sm font-medium border', SCORE_COLORS[lead.score])}>
            {lead.score.charAt(0).toUpperCase() + lead.score.slice(1)}
          </span>
          <span className={clsx('px-3 py-1 rounded-full text-sm font-medium', STATUS_COLORS[lead.status])}>
            {STATUS_LABELS[lead.status]}
          </span>
        </div>

        {/* Details */}
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-500">Location</p>
              <p className="font-medium">{lead.location || 'Not specified'}</p>
            </div>
            <div>
              <p className="text-gray-500">Budget</p>
              <p className="font-medium">{lead.budget_range || 'Not specified'}</p>
            </div>
            <div>
              <p className="text-gray-500">Urgency</p>
              <p className="font-medium">{lead.urgency || 'Not specified'}</p>
            </div>
            <div>
              <p className="text-gray-500">Source</p>
              <p className="font-medium">{lead.source?.replace('_', ' ').toUpperCase() || 'Unknown'}</p>
            </div>
          </div>
        </div>

        {/* Appointment */}
        {lead.appointment_at && (
          <div className="bg-indigo-50 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <CalendarIcon className="h-5 w-5 text-indigo-600" />
              <span className="font-medium text-indigo-900">
                Appointment: {format(parseISO(lead.appointment_at), 'MMM d, yyyy h:mm a')}
              </span>
            </div>
          </div>
        )}

        {/* Recent Conversations */}
        <div>
          <h4 className="font-medium text-gray-900 mb-3">Recent Conversations</h4>
          {conversations.length > 0 ? (
            <div className="space-y-2">
              {conversations.slice(0, 3).map((conv) => (
                <Link
                  key={conv.id}
                  to={`/conversations/${conv.id}`}
                  className="block p-3 bg-gray-50 hover:bg-gray-100 rounded-lg"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <ChatBubbleLeftRightIcon className="h-4 w-4 text-gray-400" />
                      <span className="text-sm font-medium">{conv.channel.replace('_', ' ')}</span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {format(parseISO(conv.created_at), 'MMM d')}
                    </span>
                  </div>
                  {conv.summary && (
                    <p className="text-sm text-gray-600 mt-1 truncate">{conv.summary}</p>
                  )}
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No conversations yet</p>
          )}
        </div>

        {/* Timeline */}
        <div>
          <h4 className="font-medium text-gray-900 mb-3">Activity</h4>
          <div className="text-sm text-gray-500 space-y-2">
            <p>Created: {format(parseISO(lead.created_at), 'MMM d, yyyy h:mm a')}</p>
            <p>Updated: {format(parseISO(lead.updated_at), 'MMM d, yyyy h:mm a')}</p>
            {lead.handed_off_at && (
              <p>Handed off: {format(parseISO(lead.handed_off_at), 'MMM d, yyyy h:mm a')}</p>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="border-t border-gray-200 p-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <select
            value={lead.score}
            onChange={(e) => updateLeadMutation.mutate({ score: e.target.value as LeadScore })}
            className="block w-full rounded-lg border-gray-300 text-sm"
          >
            <option value="hot">🔥 Hot</option>
            <option value="warm">🌤️ Warm</option>
            <option value="cold">❄️ Cold</option>
            <option value="unscored">⚪ Unscored</option>
          </select>
          <select
            value={lead.status}
            onChange={(e) => updateLeadMutation.mutate({ status: e.target.value as LeadStatus })}
            className="block w-full rounded-lg border-gray-300 text-sm"
          >
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => handoffMutation.mutate()}
          disabled={lead.status === 'handed_off' || handoffMutation.isPending}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {handoffMutation.isPending ? 'Handing off...' : 'Hand Off to Sales'}
        </button>
      </div>
    </div>
  );
}

function LeadRow({ lead, onClick }: { lead: Lead; onClick: () => void }) {
  return (
    <tr 
      onClick={onClick}
      className="hover:bg-gray-50 cursor-pointer border-b border-gray-100"
    >
      <td className="px-4 py-3">
        <div className="flex items-center space-x-3">
          <div
            className={clsx(
              'h-2 w-2 rounded-full flex-shrink-0',
              lead.score === 'hot' && 'bg-red-500',
              lead.score === 'warm' && 'bg-yellow-500',
              lead.score === 'cold' && 'bg-blue-500',
              lead.score === 'unscored' && 'bg-gray-400'
            )}
          />
          <div>
            <p className="font-medium text-gray-900">{lead.name || 'Unknown'}</p>
            <p className="text-sm text-gray-500">{lead.email || lead.phone}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <span className={clsx('px-2 py-1 rounded-full text-xs font-medium border', SCORE_COLORS[lead.score])}>
          {lead.score}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', STATUS_COLORS[lead.status])}>
          {STATUS_LABELS[lead.status]}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {lead.source?.replace('_', ' ').toUpperCase() || '-'}
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">
        {lead.service_interest || '-'}
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {format(parseISO(lead.created_at), 'MMM d, h:mm a')}
      </td>
    </tr>
  );
}

export default function LeadsPage() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentClient } = useClientStore();

  const [search, setSearch] = useState('');
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  
  // Get filters from URL
  const scoreFilter = searchParams.get('score') as LeadScore | null;
  const statusFilter = searchParams.get('status') as LeadStatus | null;
  const page = parseInt(searchParams.get('page') || '1', 10);

  // Fetch leads
  const {
    data: leadsData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['leads', currentClient?.id, scoreFilter, statusFilter, search, page],
    queryFn: () => leadsApi.list(
      currentClient?.id || '',
      {
        score: scoreFilter || undefined,
        status: statusFilter || undefined,
        search: search || undefined,
      },
      page,
      20
    ),
    enabled: !!currentClient?.id,
    staleTime: 30000,
  });

  // Fetch single lead if ID in URL
  const { data: singleLead } = useQuery({
    queryKey: ['lead', id],
    queryFn: () => leadsApi.get(id!),
    enabled: !!id,
  });

  // Set selected lead when URL has ID
  useMemo(() => {
    if (singleLead) {
      setSelectedLead(singleLead);
    }
  }, [singleLead]);

  const leads = leadsData?.items || [];
  const totalPages = leadsData?.pages || 1;

  const handleFilterChange = (key: string, value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    newParams.set('page', '1');
    setSearchParams(newParams);
  };

  const handlePageChange = (newPage: number) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('page', newPage.toString());
    setSearchParams(newParams);
  };

  if (!currentClient) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a client to view leads</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
          <p className="text-gray-500">Manage and track your leads</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <ArrowPathIcon className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 bg-white p-4 rounded-xl border border-gray-200">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search leads..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <select
          value={scoreFilter || ''}
          onChange={(e) => handleFilterChange('score', e.target.value || null)}
          className="px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Scores</option>
          <option value="hot">🔥 Hot</option>
          <option value="warm">🌤️ Warm</option>
          <option value="cold">❄️ Cold</option>
        </select>

        <select
          value={statusFilter || ''}
          onChange={(e) => handleFilterChange('status', e.target.value || null)}
          className="px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Statuses</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        {(scoreFilter || statusFilter) && (
          <button
            onClick={() => {
              setSearchParams(new URLSearchParams());
            }}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
            <p className="mt-2 text-gray-500">Loading leads...</p>
          </div>
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-red-600">Failed to load leads</p>
            <button onClick={() => refetch()} className="mt-2 text-blue-600 hover:underline">
              Try again
            </button>
          </div>
        ) : leads.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">No leads found</p>
          </div>
        ) : (
          <table className="min-w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Contact</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Interest</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <LeadRow
                  key={lead.id}
                  lead={lead}
                  onClick={() => setSelectedLead(lead)}
                />
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
            <p className="text-sm text-gray-500">
              Page {page} of {totalPages}
            </p>
            <div className="flex space-x-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page === 1}
                className="p-2 border border-gray-300 rounded-lg disabled:opacity-50"
              >
                <ChevronLeftIcon className="h-4 w-4" />
              </button>
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page === totalPages}
                className="p-2 border border-gray-300 rounded-lg disabled:opacity-50"
              >
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Lead Detail Panel */}
      {selectedLead && (
        <>
          <div 
            className="fixed inset-0 bg-black/30 z-40"
            onClick={() => setSelectedLead(null)}
          />
          <LeadDetailPanel
            lead={selectedLead}
            onClose={() => setSelectedLead(null)}
          />
        </>
      )}
    </div>
  );
}
